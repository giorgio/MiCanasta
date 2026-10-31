"""Canastas: plan de compras mensual, tiendas cercanas y recetas con IA.

Flujo en pasos:
  1. Inicio: presupuesto, personas y ciudad.
  2. Tiendas cerca: mapa fijo (tiendas en verde, tú en rojo) y comparación de precios.
  3. Tu lista del mes, armada con esas tiendas y esos precios.
  Aparte: ¿Qué cocino hoy? (recetas con lo que hay en casa).

Ejecutar en local:  streamlit run app.py
La clave de Gemini va en .streamlit/secrets.toml (local) o en los Secrets de
Streamlit Community Cloud, nunca en el código.
"""

import csv
import io
import time

import pydeck as pdk
import streamlit as st

import nucleo as n
import ubicacion as u

try:  # componente para leer el GPS del navegador
    from streamlit_js_eval import get_geolocation
except Exception:  # noqa: BLE001
    get_geolocation = None

st.set_page_config(page_title="Canastas", page_icon="🛒", layout="centered")

VERDE = [46, 125, 50]
ROJO = [211, 47, 47]
CANASTA_BASE = ["Arroz", "Aceite", "Huevos", "Pollo entero", "Atún en lata", "Leche", "Azúcar", "Lenteja"]
EJEMPLO_RECETAS = "arroz, huevos, verde, cebolla, tomate, atún en lata, queso"
ESPERA_ENTRE_CONSULTAS = 8  # segundos, para cuidar la cuota gratuita
MAX_TIENDAS_COMPARAR = 6

INICIALES = {
    "paso": 1, "presupuesto": 150.0, "personas": 2, "ciudad": "Guayaquil, Guayas",
    "productos": CANASTA_BASE, "radio": 3, "comidas": 3,
    "restricciones": "", "en_casa": "", "in_ingredientes": "",
}
for _k, _v in INICIALES.items():
    st.session_state.setdefault(_k, _v)

ERRORES_GPS = {
    0: "Tu navegador no permite leer la ubicación. Usaremos la ciudad que escribiste.",
    1: "No diste permiso para usar tu ubicación. Usaremos la ciudad que escribiste.",
    2: "No se pudo obtener tu ubicación. Usaremos la ciudad que escribiste.",
    3: "El GPS tardó demasiado. Usaremos la ciudad que escribiste.",
}


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def ir(paso):
    st.session_state["paso"] = paso


def obtener_cliente():
    try:
        clave = st.secrets["GEMINI_API_KEY"]
    except Exception:  # noqa: BLE001
        clave = None
    if not clave:
        st.error(
            "La app no tiene configurada la clave de la IA (GEMINI_API_KEY). "
            "Si eres el dueño, agrégala en Settings → Secrets de Streamlit Cloud."
        )
        st.stop()
    from google import genai

    return genai.Client(api_key=clave)


def puede_consultar() -> bool:
    """Deja pasar unos segundos entre consultas para no agotar la cuota gratuita."""
    falta = ESPERA_ENTRE_CONSULTAS - (time.time() - st.session_state.get("ultima_consulta", 0))
    if falta > 0:
        time.sleep(falta)
    st.session_state["ultima_consulta"] = time.time()
    return True


def alto(filas: list) -> int:
    """Altura para mostrar la tabla completa, sin barra de desplazamiento."""
    return 38 + 35 * max(len(filas), 1) + 3


def csv_de(filas: list[dict]) -> bytes:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(filas[0].keys()))
    w.writeheader()
    w.writerows(filas)
    return buf.getvalue().encode("utf-8-sig")


@st.cache_data(ttl=86400, show_spinner=False)
def geocodificar(lugar: str):
    return u.geocodificar(lugar)


@st.cache_data(ttl=3600, show_spinner=False)
def buscar_cercanas(lat: float, lon: float, radio: float):
    return u.tiendas_cercanas(lat, lon, radio)


def mapa_fijo(lat: float, lon: float, radio_km: float, tiendas: list[dict]):
    """Mapa que no se puede mover ni acercar: tiendas en verde, tu ubicación en rojo."""
    capas = [
        pdk.Layer(  # círculo del radio de búsqueda
            "ScatterplotLayer", data=[{"lat": lat, "lon": lon}], get_position="[lon, lat]",
            get_radius=radio_km * 1000, filled=False, stroked=True,
            get_line_color=ROJO, line_width_min_pixels=1, opacity=0.35,
        ),
        pdk.Layer(
            "ScatterplotLayer",
            data=[{"lat": t["lat"], "lon": t["lon"], "nombre": t["nombre"], "info": f"{t['tipo']} · {t['distancia_km']} km"}
                  for t in tiendas],
            get_position="[lon, lat]", get_fill_color=VERDE, get_line_color=[255, 255, 255],
            stroked=True, line_width_min_pixels=1, radius_min_pixels=6, radius_max_pixels=9, pickable=True,
        ),
        pdk.Layer(  # tú: punto rojo grande con borde blanco
            "ScatterplotLayer", data=[{"lat": lat, "lon": lon, "nombre": "Estás aquí", "info": ""}],
            get_position="[lon, lat]", get_fill_color=ROJO, get_line_color=[255, 255, 255],
            stroked=True, line_width_min_pixels=2, radius_min_pixels=9, radius_max_pixels=11, pickable=True,
        ),
    ]
    deck = pdk.Deck(
        layers=capas,
        initial_view_state=pdk.ViewState(latitude=lat, longitude=lon, zoom=u.zoom_para_radio(lat, radio_km)),
        views=[pdk.View(type="MapView", controller=False)],  # sin mover ni zoom
        tooltip={"text": "{nombre}\n{info}"},
        map_style="light",
    )
    st.pydeck_chart(deck, height=380)
    st.caption("🟢 Tiendas · 🔴 Tú · El círculo marca el radio de búsqueda.")


# ---------------------------------------------------------------------------
# Cabecera
# ---------------------------------------------------------------------------

st.title("🛒 Canastas")

paso = st.session_state["paso"]
if paso in (1, 2, 3):
    st.progress(paso / 3, text=["", "Paso 1 de 3 · Tus datos", "Paso 2 de 3 · Tiendas y precios",
                                "Paso 3 de 3 · Tu lista del mes"][paso])

with st.sidebar:
    st.header("Menú")
    st.button("🧾 Mi compra del mes", on_click=ir, args=(1,), width="stretch")
    st.button("🍳 ¿Qué cocino hoy?", on_click=ir, args=("recetas",), width="stretch")
    st.divider()
    st.info(
        "Los precios son **estimaciones** hechas por IA. Usa los enlaces **Ver precio** para confirmar "
        "el precio de hoy. La información nutricional es aproximada."
    )
    st.caption("No escribas datos personales: lo que ingresas se envía a la IA de Google.")


# ---------------------------------------------------------------------------
# Paso 1: inicio sencillo
# ---------------------------------------------------------------------------

def paso_inicio():
    st.write("Dime cuánto tienes para la comida del mes y te digo **dónde comprar más barato** y **qué comprar**.")
    with st.form("form_inicio", border=True):
        pres = st.number_input("💵 ¿Cuál es tu presupuesto mensual para comida? (USD)", min_value=0.0,
                               max_value=10000.0, step=10.0, value=float(st.session_state["presupuesto"]))
        pers = st.number_input("👨‍👩‍👧 ¿Cuántas personas comen en casa?", min_value=1, max_value=15,
                               value=int(st.session_state["personas"]))
        ciudad = st.text_input("📍 ¿En qué ciudad o barrio vives?", placeholder="Ej.: Urdesa, Guayaquil",
                               value=st.session_state["ciudad"])
        seguir = st.form_submit_button("Continuar →", type="primary", width="stretch")
    if seguir:
        val = n.validar_plan(pres, pers, ["-"])
        if not ciudad.strip():
            val.errores.append("Escribe tu ciudad o barrio.")
        for e in val.errores:
            st.error(e)
        if val.ok:
            st.session_state.update(presupuesto=pres, personas=pers, ciudad=ciudad.strip())
            for k in ("punto", "comparacion", "resultado"):
                st.session_state.pop(k, None)
            ir(2)
            st.rerun()


# ---------------------------------------------------------------------------
# Paso 2: tiendas cercanas + comparación automática
# ---------------------------------------------------------------------------

def ubicar():
    """Fija el punto de búsqueda: GPS si se pidió, si no la ciudad del paso 1."""
    if st.session_state.get("pedir_gps") and get_geolocation:
        loc = get_geolocation()
        if not loc:
            st.info("Esperando tu ubicación… si el navegador pregunta, pulsa **Permitir**.")
            st.stop()
        st.session_state["pedir_gps"] = False
        if "error" in loc:
            st.warning(ERRORES_GPS.get(loc["error"].get("code"), ERRORES_GPS[2]))
        else:
            c = loc["coords"]
            st.session_state["punto"] = (c["latitude"], c["longitude"], "tu ubicación actual")
            st.session_state.pop("comparacion", None)
    if "punto" not in st.session_state:
        try:
            st.session_state["punto"] = geocodificar(st.session_state["ciudad"].strip())
        except u.ErrorMapa as e:
            st.error(str(e))
            st.button("← Cambiar ciudad", on_click=ir, args=(1,))
            st.stop()


def comparar_cercanas(tiendas: list[dict]):
    """Compara los productos elegidos en los tipos de tienda que hay cerca."""
    categorias = []
    for t in tiendas:  # ya vienen ordenadas por distancia
        c = u.categoria(t)
        if c and c not in categorias and c in n.TIENDAS_DISPONIBLES:
            categorias.append(c)
    categorias = categorias[:MAX_TIENDAS_COMPARAR]
    clave = (tuple(st.session_state["productos"]), tuple(categorias), st.session_state["ciudad"])
    previa = st.session_state.get("comparacion")
    if previa and previa["clave"] == clave:
        return previa
    if not categorias:
        return None
    if not puede_consultar():
        st.stop()
    cliente = obtener_cliente()
    with st.spinner("Comparando precios en las tiendas cercanas… unos 20 segundos"):
        try:
            comp, _ = n.comparar_precios(cliente, st.session_state["productos"], categorias,
                                         st.session_state["ciudad"])
        except n.ErrorIA as e:
            st.error(str(e))
            st.stop()
    datos = {"clave": clave, "comp": comp, "categorias": categorias,
             "con_precio": n.tiendas_con_precio(comp, categorias)}
    st.session_state["comparacion"] = datos
    return datos


def paso_tiendas():
    st.button("← Cambiar mis datos", on_click=ir, args=(1,))
    with st.container(border=True):
        st.session_state["productos"] = st.multiselect(
            "🛍️ ¿Qué productos quieres comparar?", n.PRODUCTOS_COMUNES, default=st.session_state["productos"],
            accept_new_options=True, max_selections=n.MAX_PRODUCTOS_COMPARAR)
        c1, c2 = st.columns([1, 1])
        if c1.button("📡 Usar mi ubicación (GPS)", disabled=get_geolocation is None, width="stretch"):
            st.session_state["pedir_gps"] = True
        st.session_state["radio"] = c2.select_slider(
            "Distancia máxima", options=[1, 2, 3, 5, 8, 12], value=st.session_state["radio"],
            format_func=lambda x: f"{x} km")
    if not st.session_state["productos"]:
        st.warning("Elige al menos un producto para comparar.")
        return

    ubicar()
    lat, lon, nombre = st.session_state["punto"]
    radio = st.session_state["radio"]
    try:
        with st.spinner("Buscando tiendas cercanas en el mapa…"):
            cercanas = buscar_cercanas(round(lat, 4), round(lon, 4), float(radio))
    except u.ErrorMapa as e:
        st.error(str(e))
        return
    st.session_state["cercanas"] = cercanas

    st.subheader(f"📍 Tiendas a menos de {radio} km de {nombre.split(',')[0]}")
    datos = comparar_cercanas(cercanas) if cercanas else None
    con_precio = set(datos["con_precio"]) if datos else set()
    visibles = [t for t in cercanas if u.categoria(t) in con_precio]  # sin precio, fuera de la lista
    mapa_fijo(lat, lon, radio, visibles)

    if not visibles:
        st.info("No encontré tiendas con precios en esa distancia. Aumenta la distancia o cambia de barrio.")
        return

    comp, cats = datos["comp"], datos["con_precio"]
    resumen = n.resumen_por_tienda(comp, cats)
    filas, _, ganadas = n.tabla_comparacion(comp, cats)
    nprod = len(comp.filas)

    st.subheader("💰 Tus productos, comparados")
    barata = cats[0]
    st.success(f"Para tus {nprod} productos, lo más barato cerca de ti es **{barata}**: "
               f"unos **{resumen[barata]['total']:.2f} USD**. {comp.nota}")
    st.dataframe(
        filas, hide_index=True, width="stretch", height=alto(filas),
        column_config={t: st.column_config.NumberColumn(t, format="$%.2f") for t in cats}
        | {"Ahorro vs. más caro": st.column_config.NumberColumn(format="$%.2f")},
    )

    st.subheader(f"🏪 {len(visibles)} tiendas cercanas con precios")
    lista = []
    for t in visibles:
        r = resumen[u.categoria(t)]
        lista.append({
            "Tienda": t["nombre"], "Tipo": u.categoria(t), "Distancia": f"{t['distancia_km']} km",
            "Tus productos": round(r["total"], 2), "Con precio": f"{r['con_precio']} de {nprod}",
            "Cómo llegar": u.enlace_mapa(t["lat"], t["lon"], t["nombre"]),
        })
    lista.sort(key=lambda x: (-int(x["Con precio"].split()[0]), x["Tus productos"], float(x["Distancia"].split()[0])))
    st.dataframe(
        lista, hide_index=True, width="stretch", height=alto(lista),
        column_config={"Tus productos": st.column_config.NumberColumn(format="$%.2f"),
                       "Cómo llegar": st.column_config.LinkColumn(display_text="Abrir mapa")},
    )
    with st.expander("Ver el precio de hoy en la web de cada tienda"):
        for f in filas:
            enlaces = " · ".join(f"[{t}]({u.enlace_precio(f['Producto'], t)})" for t in cats)
            st.markdown(f"**{f['Producto']}** ({f['Presentación']}): {enlaces}")
    st.caption("Precios estimados por IA. Confírmalos con los enlaces o en la tienda.")

    st.button("Armar mi lista del mes con estas tiendas →", type="primary", width="stretch",
              on_click=ir, args=(3,))


# ---------------------------------------------------------------------------
# Paso 3: lista del mes
# ---------------------------------------------------------------------------

def paso_lista():
    st.button("← Volver a las tiendas", on_click=ir, args=(2,))
    datos = st.session_state.get("comparacion")
    tiendas = datos["con_precio"] if datos else ["Mercado municipal", "Tía", "Supermaxi"]
    pres, personas = st.session_state["presupuesto"], st.session_state["personas"]
    st.write(f"**{pres:.2f} USD** para **{personas}** persona(s) en **{st.session_state['ciudad']}** · "
             f"Tiendas: {', '.join(tiendas)}")

    with st.expander("Ajustar mi lista (opcional)"):
        st.session_state["comidas"] = st.selectbox("Comidas al día", [2, 3, 4],
                                                   index=[2, 3, 4].index(st.session_state["comidas"]))
        st.session_state["restricciones"] = st.text_input(
            "Preferencias o restricciones", value=st.session_state["restricciones"],
            placeholder="Ej.: vegetariano, sin cerdo, hay un bebé")
        st.session_state["en_casa"] = st.text_input("¿Qué ya tienes en casa?", value=st.session_state["en_casa"],
                                                    placeholder="Ej.: 2 kg de arroz, aceite")
        rehacer = st.button("Volver a armar la lista")

    for a in n.validar_plan(pres, personas, tiendas).avisos:
        st.warning(a)

    if "resultado" not in st.session_state or rehacer:
        if not puede_consultar():
            return
        cliente = obtener_cliente()
        precios = n.precios_como_texto(datos["comp"], tiendas) if datos else ""
        with st.spinner("Armando tu lista del mes… puede tardar hasta un minuto. No cierres la página."):
            try:
                st.session_state["resultado"] = n.generar_plan(
                    cliente, pres, personas, st.session_state["comidas"], st.session_state["ciudad"], tiendas,
                    st.session_state["restricciones"], st.session_state["en_casa"], precios,
                    cercanas=u.resumen_cercanas(st.session_state.get("cercanas", [])),
                )
            except n.ErrorIA as e:
                st.error(str(e))
                return

    res = st.session_state["resultado"]
    plan = res["plan"]
    m1, m2, m3 = st.columns(3)
    m1.metric("Presupuesto", f"{pres:.2f} USD")
    m2.metric("Total estimado", f"{res['total']:.2f} USD")
    m3.metric("Te sobra", f"{res['sobrante']:.2f} USD")
    if res["dentro_presupuesto"]:
        st.success(plan.resumen)
    else:
        st.error(f"Aun ajustada, la lista cuesta {res['total']:.2f} USD y se pasa {-res['sobrante']:.2f} USD. "
                 "Aumenta el presupuesto o pulsa «Volver a armar la lista».")
    for a in res["avisos"]:
        st.warning(a)

    filas = n.tabla_items(plan.items)
    st.subheader("🧾 Lista de compras por tienda")
    st.dataframe(filas, width="stretch", hide_index=True, height=alto(filas),
                 column_config={"Ver precio hoy": st.column_config.LinkColumn(display_text="Ver precio")})
    st.bar_chart(n.totales_por_tienda(plan.items), horizontal=True)
    d1, d2 = st.columns(2)
    d1.download_button("Descargar (Excel/CSV)", csv_de(filas), "lista_compras.csv", "text/csv", width="stretch")
    d2.download_button("Descargar para imprimir", n.plan_a_texto(res, pres).encode("utf-8"),
                       "lista_compras.txt", "text/plain", width="stretch")
    with st.expander("Menú de ejemplo para una semana"):
        st.dataframe([{"Día": c.dia, "Desayuno": c.desayuno, "Almuerzo": c.almuerzo, "Merienda": c.merienda}
                      for c in plan.menu_semana_ejemplo], width="stretch", hide_index=True)
    st.subheader("💡 Consejos para ahorrar")
    for c in plan.consejos:
        st.markdown(f"- {c}")
    st.button("🍳 ¿Qué cocino hoy con lo que tengo?", on_click=ir, args=("recetas",), width="stretch")


# ---------------------------------------------------------------------------
# Recetas
# ---------------------------------------------------------------------------

def cargar_ejemplo_recetas():
    st.session_state["in_ingredientes"] = EJEMPLO_RECETAS


def pagina_recetas():
    st.button("← Volver", on_click=ir, args=(1,))
    st.subheader("🍳 ¿Qué cocino hoy?")
    st.button("Usar ingredientes de ejemplo", on_click=cargar_ejemplo_recetas)
    with st.form("form_recetas"):
        ingredientes = st.text_area("¿Qué tienes en la cocina? Sepáralo con comas",
                                    placeholder="Ej.: arroz, huevos, verde, cebolla, tomate", key="in_ingredientes")
        r1, r2 = st.columns(2)
        personas_r = r1.number_input("¿Para cuántas personas?", min_value=1, max_value=15,
                                     value=int(st.session_state["personas"]))
        restr_r = r2.text_input("Preferencias (opcional)", placeholder="Ej.: sin picante")
        pedir = st.form_submit_button("Dame recetas", type="primary")
    if pedir:
        val = n.validar_recetas(ingredientes)
        for e in val.errores:
            st.error(e)
        if val.ok and puede_consultar():
            for a in val.avisos:
                st.warning(a)
            cliente = obtener_cliente()
            with st.spinner("Buscando recetas con lo que tienes…"):
                try:
                    st.session_state["recetas"], _ = n.generar_recetas(cliente, ingredientes, personas_r, restr_r)
                except n.ErrorIA as e:
                    st.error(str(e))
    rec = st.session_state.get("recetas")
    if rec:
        if rec.aviso:
            st.warning(rec.aviso)
        for r in rec.recetas:
            with st.container(border=True):
                st.subheader(r.nombre)
                a, b, c = st.columns(3)
                a.metric("Porciones", r.porciones)
                b.metric("Tiempo", f"{r.tiempo_minutos} min")
                c.metric("Por porción", f"~{r.calorias_aprox_por_porcion} kcal")
                st.markdown("**Usas lo que tienes:** " + ", ".join(r.ingredientes_que_tienes))
                if r.ingredientes_faltantes:
                    st.markdown(f"**Te falta comprar (~{r.costo_faltantes_usd:.2f} USD):** "
                                + ", ".join(r.ingredientes_faltantes))
                for i, p in enumerate(r.pasos, 1):
                    st.markdown(f"{i}. {p}")
                st.caption(f"💚 {r.por_que_es_nutritiva} · {r.proteina_g_aprox_por_porcion} g de proteína por porción")


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

{1: paso_inicio, 2: paso_tiendas, 3: paso_lista, "recetas": pagina_recetas}.get(paso, paso_inicio)()

st.divider()
st.caption("Canastas · Proyecto académico · IA: Google Gemini · Mapa: © OpenStreetMap · "
           "Precios y valores nutricionales aproximados.")
