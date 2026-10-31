"""Canasta Inteligente: plan de compras mensual y recetas nutritivas con IA.

Ejecutar en local:  streamlit run app.py
La clave de Gemini va en .streamlit/secrets.toml (local) o en los Secrets de
Streamlit Community Cloud, nunca en el código.
"""

import csv
import io
import time

import streamlit as st

import nucleo as n
import ubicacion as u

try:  # componente para leer el GPS del navegador
    from streamlit_js_eval import get_geolocation
except Exception:  # noqa: BLE001
    get_geolocation = None

st.set_page_config(page_title="Canasta Inteligente", page_icon="🛒", layout="wide")

EJEMPLO = dict(
    presupuesto=250.0,
    personas=4,
    comidas=3,
    ciudad="Balao, Guayas",
    tiendas=["Mercado municipal", "Tienda de barrio", "Tía"],
    restricciones="Sin cerdo. Un niño de 6 años.",
    en_casa="2 kg de arroz, sal, 1 litro de aceite",
    precios="",
)
EJEMPLO_RECETAS = "arroz, huevos, verde, cebolla, tomate, atún en lata, queso"
ESPERA_ENTRE_CONSULTAS = 8  # segundos, para cuidar la cuota gratuita


# ---------------------------------------------------------------------------
# Utilidades de interfaz
# ---------------------------------------------------------------------------

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
    ultima = st.session_state.get("ultima_consulta", 0)
    falta = ESPERA_ENTRE_CONSULTAS - (time.time() - ultima)
    if falta > 0:
        st.warning(f"Espera {int(falta) + 1} segundos antes de volver a consultar a la IA.")
        return False
    st.session_state["ultima_consulta"] = time.time()
    return True


@st.cache_data(ttl=86400, show_spinner=False)
def geocodificar(lugar: str):
    return u.geocodificar(lugar)


@st.cache_data(ttl=3600, show_spinner=False)
def buscar_cercanas(lat: float, lon: float, radio: float):
    return u.tiendas_cercanas(lat, lon, radio)


def usar_tiendas_cercanas():
    opciones = [t for t in u.tiendas_para_plan(st.session_state.get("cercanas", [])) if t in n.TIENDAS_DISPONIBLES]
    if opciones:
        st.session_state["in_tiendas"] = opciones


ERRORES_GPS = {
    0: "Tu navegador no permite leer la ubicación. Escribe tu ciudad.",
    1: "No diste permiso para usar tu ubicación. Puedes escribir tu ciudad en su lugar.",
    2: "No se pudo obtener tu ubicación. Escribe tu ciudad.",
    3: "El GPS tardó demasiado. Intenta de nuevo o escribe tu ciudad.",
}


def seccion_ubicacion():
    with st.container(border=True):
        st.subheader("📍 Tiendas cerca de ti")
        st.caption(
            "Usa el GPS o escribe tu ciudad para ver los mercados y supermercados reales que tienes cerca "
            "(datos de OpenStreetMap). Tu ubicación solo se usa para esta búsqueda y no se guarda."
        )
        g1, g2, g3 = st.columns([1.2, 2, 1])
        if g1.button("📡 Usar mi ubicación (GPS)", disabled=get_geolocation is None):
            st.session_state["pedir_gps"] = True
        lugar = g2.text_input("…o escribe tu ciudad o barrio", placeholder="Ej.: Balao, Guayas", key="in_lugar",
                              label_visibility="collapsed")
        if g3.button("Buscar ciudad"):
            if not lugar.strip():
                st.warning("Escribe una ciudad, por ejemplo 'Balao, Guayas'.")
            else:
                try:
                    st.session_state["punto"] = geocodificar(lugar.strip())
                except u.ErrorMapa as e:
                    st.error(str(e))
        radio = st.slider("Radio de búsqueda (km)", 1, 20, 5, key="in_radio")

        if st.session_state.get("pedir_gps") and get_geolocation:
            loc = get_geolocation()
            if not loc:
                st.info("Esperando tu ubicación… si el navegador pregunta, pulsa **Permitir**.")
            elif "error" in loc:
                st.session_state["pedir_gps"] = False
                st.warning(ERRORES_GPS.get(loc["error"].get("code"), ERRORES_GPS[2]))
            else:
                c = loc["coords"]
                st.session_state["punto"] = (c["latitude"], c["longitude"], "Tu ubicación actual")
                st.session_state["pedir_gps"] = False

        punto = st.session_state.get("punto")
        if not punto:
            return
        lat, lon, nombre = punto
        try:
            with st.spinner("Buscando tiendas cercanas…"):
                tiendas = buscar_cercanas(round(lat, 3), round(lon, 3), float(radio))
        except u.ErrorMapa as e:
            st.error(str(e))
            return
        st.session_state["cercanas"] = tiendas
        st.markdown(f"**{len(tiendas)} tiendas** a menos de {radio} km de *{nombre}*.")
        if not tiendas:
            st.info("No hay tiendas registradas en el mapa en esa zona. Aumenta el radio o elige tus tiendas a mano.")
            return
        import pandas as pd

        puntos = pd.DataFrame(
            [{"lat": lat, "lon": lon, "color": "#1565C0", "size": 60}]
            + [{"lat": t["lat"], "lon": t["lon"],
                "color": "#2E7D32" if t["cadena"] or t["tipo"] == "Mercado" else "#9E9E9E", "size": 30}
               for t in tiendas[:150]]
        )
        st.map(puntos, latitude="lat", longitude="lon", color="color", size="size")
        st.caption("Punto azul: tu búsqueda. Verde: supermercados y mercados. Gris: otras tiendas.")
        st.dataframe(
            [{"Tienda": t["nombre"], "Tipo": t["tipo"], "Cadena": t["cadena"] or "", "Distancia (km)": t["distancia_km"],
              "Cómo llegar": u.enlace_mapa(t["lat"], t["lon"], t["nombre"])} for t in tiendas[:40]],
            hide_index=True, width="stretch",
            column_config={"Cómo llegar": st.column_config.LinkColumn("Cómo llegar", display_text="Abrir mapa")},
        )
        sugeridas = [t for t in u.tiendas_para_plan(tiendas) if t in n.TIENDAS_DISPONIBLES]
        if sugeridas:
            st.button(f"Usar estas tiendas en mi lista: {', '.join(sugeridas)}", on_click=usar_tiendas_cercanas,
                      type="primary")


def csv_de(filas: list[dict]) -> bytes:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(filas[0].keys()))
    w.writeheader()
    w.writerows(filas)
    return buf.getvalue().encode("utf-8-sig")


VALORES_INICIALES = dict(
    presupuesto=150.0, personas=2, comidas=3, ciudad="",
    tiendas=["Mercado municipal", "Tía"], restricciones="", en_casa="", precios="",
)
for _k, _v in VALORES_INICIALES.items():
    st.session_state.setdefault(f"in_{_k}", _v)
st.session_state.setdefault("in_ingredientes", "")


def cargar_ejemplo_recetas():
    st.session_state["in_ingredientes"] = EJEMPLO_RECETAS


def cargar_ejemplo():
    for k, v in EJEMPLO.items():
        st.session_state[f"in_{k}"] = v


# ---------------------------------------------------------------------------
# Cabecera y barra lateral
# ---------------------------------------------------------------------------

st.title("🛒 Canasta Inteligente")
st.write(
    "Dime cuánto tienes para la comida del mes y te ayudo a decidir **qué comprar, "
    "dónde comprarlo y qué cocinar** con lo que ya tienes."
)

with st.sidebar:
    st.header("Cómo se usa")
    st.markdown(
        "1. En **Mi compra del mes**, escribe tu presupuesto y cuántas personas comen.\n"
        "2. Marca las tiendas a las que puedes ir.\n"
        "3. Pulsa **Armar mi lista**.\n"
        "4. En **¿Qué cocino hoy?**, escribe lo que tienes en casa y pide recetas.\n\n"
        "¿Primera vez? Pulsa **Cargar ejemplo** para ver cómo funciona."
    )
    st.info(
        "Los precios son **estimaciones** hechas por IA. Usa los enlaces **Ver precio** para confirmar el precio de hoy. "
        "La información nutricional es aproximada y no reemplaza a un profesional de salud."
    )
    st.caption("No escribas datos personales: lo que ingresas se envía a la IA de Google.")

tab_plan, tab_recetas = st.tabs(["🧾 Mi compra del mes", "🍳 ¿Qué cocino hoy?"])

# ---------------------------------------------------------------------------
# Pestaña 1: plan de compras
# ---------------------------------------------------------------------------

with tab_plan:
    seccion_ubicacion()
    st.button("Cargar ejemplo", on_click=cargar_ejemplo, help="Llena el formulario con un hogar de ejemplo")

    with st.form("form_plan"):
        c1, c2, c3 = st.columns(3)
        presupuesto = c1.number_input(
            "Presupuesto mensual para comida (USD)", min_value=0.0, max_value=10000.0,
            step=10.0, key="in_presupuesto",
        )
        personas = c2.number_input("¿Cuántas personas comen?", min_value=1, max_value=15, key="in_personas")
        comidas = c3.selectbox("Comidas al día", [2, 3, 4], key="in_comidas")

        ciudad = st.text_input("Ciudad o sector (opcional)", placeholder="Ej.: Balao, Guayas", key="in_ciudad")
        tiendas = st.multiselect(
            "¿Dónde puedes comprar?", n.TIENDAS_DISPONIBLES, key="in_tiendas",
        )
        restricciones = st.text_input(
            "Preferencias o restricciones (opcional)",
            placeholder="Ej.: vegetariano, sin lactosa, hay un bebé...", key="in_restricciones",
        )
        en_casa = st.text_input(
            "¿Qué ya tienes en casa? (opcional)", placeholder="Ej.: 2 kg de arroz, aceite", key="in_en_casa",
        )
        precios = st.text_input(
            "Precios que viste hoy (opcional, la lista los respetará)",
            placeholder="Ej.: cubeta de huevos 4.50 en el mercado; arroz 5 kg 6.20 en Tía", key="in_precios",
        )
        enviar = st.form_submit_button("Armar mi lista", type="primary")

    if enviar:
        val = n.validar_plan(presupuesto, personas, tiendas)
        for e in val.errores:
            st.error(e)
        if val.ok and puede_consultar():
            for a in val.avisos:
                st.warning(a)
            cliente = obtener_cliente()
            with st.spinner("Armando tu lista del mes... puede tardar unos 20 segundos"):
                try:
                    st.session_state["resultado"] = n.generar_plan(
                        cliente, presupuesto, personas, comidas, ciudad, tiendas,
                        restricciones, en_casa, precios,
                        cercanas=u.resumen_cercanas(st.session_state.get("cercanas", [])),
                    )
                    st.session_state["presupuesto_usado"] = presupuesto
                except n.ErrorIA as e:
                    st.error(str(e))

    res = st.session_state.get("resultado")
    if res:
        plan = res["plan"]
        pres = st.session_state["presupuesto_usado"]
        st.divider()
        m1, m2, m3 = st.columns(3)
        m1.metric("Presupuesto", f"{pres:.2f} USD")
        m2.metric("Total estimado", f"{res['total']:.2f} USD")
        m3.metric("Te sobra", f"{res['sobrante']:.2f} USD")

        if res["dentro_presupuesto"]:
            st.success(plan.resumen)
        else:
            st.error(
                f"Aun después de ajustarla, la lista cuesta {res['total']:.2f} USD y se pasa "
                f"{-res['sobrante']:.2f} USD de tu presupuesto. Quita productos de la tabla o "
                "aumenta el presupuesto."
            )
        if res["corregido"] and res["dentro_presupuesto"]:
            st.caption("La primera propuesta se pasaba del presupuesto; la app pidió a la IA que la ajustara.")
        for a in res["avisos"]:
            st.warning(a)

        filas = n.tabla_items(plan.items)
        st.subheader("Lista de compras por tienda")
        st.caption("Los precios son estimados. Pulsa **Ver precio** para revisar el precio de hoy en la tienda.")
        st.dataframe(
            filas, width="stretch", hide_index=True,
            column_config={"Ver precio hoy": st.column_config.LinkColumn("Ver precio hoy", display_text="Ver precio")},
        )

        st.subheader("Cuánto gastarás en cada tienda")
        st.bar_chart(n.totales_por_tienda(plan.items), horizontal=True)

        d1, d2 = st.columns(2)
        d1.download_button("Descargar lista (Excel/CSV)", csv_de(filas), "lista_compras.csv", "text/csv")
        d2.download_button(
            "Descargar lista para imprimir (TXT)", n.plan_a_texto(res, pres).encode("utf-8"),
            "lista_compras.txt", "text/plain",
        )

        with st.expander("Menú de ejemplo para una semana"):
            st.dataframe(
                [{"Día": c.dia, "Desayuno": c.desayuno, "Almuerzo": c.almuerzo, "Merienda": c.merienda}
                 for c in plan.menu_semana_ejemplo],
                width="stretch", hide_index=True,
            )
        st.subheader("Consejos para ahorrar")
        for c in plan.consejos:
            st.markdown(f"- {c}")

# ---------------------------------------------------------------------------
# Pestaña 2: recetas con lo que hay en casa
# ---------------------------------------------------------------------------

with tab_recetas:
    st.button("Usar ingredientes de ejemplo", on_click=cargar_ejemplo_recetas)

    with st.form("form_recetas"):
        ingredientes = st.text_area(
            "¿Qué tienes en la cocina? Sepáralo con comas",
            placeholder="Ej.: arroz, huevos, verde, cebolla, tomate", key="in_ingredientes",
        )
        r1, r2 = st.columns(2)
        personas_r = r1.number_input("¿Para cuántas personas?", min_value=1, max_value=15, value=2)
        restr_r = r2.text_input("Preferencias o restricciones (opcional)", placeholder="Ej.: sin picante")
        pedir = st.form_submit_button("Dame recetas", type="primary")

    if pedir:
        val = n.validar_recetas(ingredientes)
        for e in val.errores:
            st.error(e)
        if val.ok and puede_consultar():
            for a in val.avisos:
                st.warning(a)
            cliente = obtener_cliente()
            with st.spinner("Buscando recetas con lo que tienes..."):
                try:
                    st.session_state["recetas"], _ = n.generar_recetas(cliente, ingredientes, personas_r, restr_r)
                except n.ErrorIA as e:
                    st.error(str(e))

    rec = st.session_state.get("recetas")
    if rec:
        if rec.aviso:
            st.warning(rec.aviso)
        if not rec.recetas and not rec.aviso:
            st.warning("No se encontraron recetas con esos ingredientes. Prueba agregando más.")
        for r in rec.recetas:
            with st.container(border=True):
                st.subheader(r.nombre)
                a, b, c = st.columns(3)
                a.metric("Porciones", r.porciones)
                b.metric("Tiempo", f"{r.tiempo_minutos} min")
                c.metric("Por porción", f"~{r.calorias_aprox_por_porcion} kcal · {r.proteina_g_aprox_por_porcion} g prot.")
                st.markdown("**Usas lo que tienes:** " + ", ".join(r.ingredientes_que_tienes))
                if r.ingredientes_faltantes:
                    st.markdown(
                        f"**Te falta comprar (~{r.costo_faltantes_usd:.2f} USD):** "
                        + ", ".join(r.ingredientes_faltantes)
                    )
                st.markdown("**Preparación:**")
                for i, paso in enumerate(r.pasos, 1):
                    st.markdown(f"{i}. {paso}")
                st.caption("💚 " + r.por_que_es_nutritiva)

st.divider()
st.caption("Canasta Inteligente · Proyecto académico · IA: Google Gemini · Precios y valores nutricionales aproximados.")
