"""Diseño visual de Canastas: estilos, cabecera, títulos, indicador de pasos y menú.

Colores y fuente base están en .streamlit/config.toml; aquí van los detalles que
el tema no cubre. Todo es solo presentación: no hay lógica de la app.
"""

import streamlit as st

AZUL = "#0E5A43"   # verde esmeralda profundo (color principal)
AZUL_CLARO = "#E0EEE7"   # verde claro
TEXTO = "#1F2A24"
GRIS = "#7A847D"
BORDE = "#E3E7DE"
FONDO = "#F4F5F0"

# Isotipo de Canastas: una "S" que baja y se convierte en canasta, con tejido (diseño de Jorge).
ISOTIPO_TRAZO = ("M30 11 C30 7.1 27 4.2 23.5 4.2 C19.8 4.2 17 7 17 10.5 C17 13.9 19.6 16.3 23.4 16.3 L40.6 16.3 "
                 "L35.2 38.2 C34.8 39.6 33.6 40.6 32.1 40.6 L15.9 40.6 C14.4 40.6 13.2 39.6 12.8 38.2 L8.6 22 L27 22")
ISOTIPO_TEJIDO = ("M18.5 28 L19.5 34.5", "M24 28 L24 34.5", "M29.5 28 L28.5 34.5")


def isotipo_svg(color: str = "#fff", tam: int = 28) -> str:
    tejido = "".join(f'<path d="{p}" stroke-width="2.6"/>' for p in ISOTIPO_TEJIDO)
    return (f'<svg width="{tam}" height="{tam}" viewBox="0 0 48 48" fill="none" stroke="{color}" '
            f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
            f'<path d="{ISOTIPO_TRAZO}" stroke-width="3.6"/>{tejido}</svg>')


ICONO_CANASTA = isotipo_svg("#fff", 30)

CSS = f"""
<style>
.block-container {{ max-width: 1240px; padding-top: 0 !important; padding-bottom: 3rem; }}
header[data-testid="stHeader"] {{ background: transparent; }}

/* Cabecera blanca a todo el ancho */
.cn-cabecera {{ display:flex; justify-content:space-between; align-items:center; gap:1rem;
  background:#fff; border-bottom:1px solid {BORDE}; padding:1.3rem 0; margin-bottom:2.4rem;
  box-shadow:0 0 0 100vmax #fff; clip-path:inset(0 -100vmax); }}
.cn-logo {{ display:flex; align-items:center; gap:.85rem; text-decoration:none; }}
.cn-logo .icono {{ width:48px; height:48px; border-radius:13px; background:{AZUL};
  display:grid; place-items:center; }}
.cn-logo .nombre {{ font-size:1.95rem; font-weight:800; letter-spacing:-.035em; color:{TEXTO}; }}
.cn-logo .punto {{ color:{AZUL}; }}
.cn-lema {{ color:{GRIS}; font-size:.95rem; }}

/* Títulos de cada pantalla */
.cn-ceja {{ font-size:.78rem; letter-spacing:.22em; font-weight:700; color:{GRIS};
  text-transform:uppercase; margin:0 0 .5rem; }}
.cn-titulo {{ font-size:clamp(2.1rem, 4.6vw, 3.3rem); font-weight:800; letter-spacing:-.045em;
  line-height:1.05; color:{TEXTO}; margin:0 0 1rem; }}
.cn-sub {{ color:{GRIS}; font-size:1.08rem; line-height:1.7; margin:0 0 1.8rem; }}

/* Indicador de pasos */
.cn-pasos {{ display:flex; align-items:center; gap:.9rem; margin:.2rem 0 1.6rem; }}
.cn-paso {{ display:flex; align-items:center; gap:.6rem; color:{GRIS}; white-space:nowrap; font-size:.98rem; }}
.cn-num {{ width:30px; height:30px; border-radius:50%; border:1.5px solid #CFD6CB;
  display:grid; place-items:center; font-size:.85rem; flex:none; }}
.cn-paso.activo {{ color:{TEXTO}; font-weight:700; }}
.cn-paso.activo .cn-num {{ background:{AZUL}; border-color:{AZUL}; color:#fff; }}
.cn-paso.hecho .cn-num {{ background:{AZUL_CLARO}; border-color:{AZUL_CLARO}; color:{AZUL}; }}
.cn-linea {{ height:1px; background:#D9DFD4; width:100%; }}
.st-key-pasos {{ margin:.2rem 0 1.4rem; }}
.st-key-pasos [data-testid="stHorizontalBlock"] {{ flex-wrap:nowrap !important; flex-direction:row !important; }}
.st-key-pasos [data-testid="stColumn"] {{ min-width:0 !important; }}
[class*="st-key-paso_"] button {{ background:transparent !important; border:none !important; box-shadow:none !important;
  padding:.2rem .3rem !important; min-height:auto !important; gap:.6rem; justify-content:flex-start; width:100%; }}
[class*="st-key-paso_"] button p {{ font-size:.98rem; color:{GRIS}; white-space:nowrap; }}
[class*="st-key-paso_"] button::before {{ width:30px; height:30px; flex:none; border-radius:50%; border:1.5px solid #CFD6CB;
  display:grid; place-items:center; font-size:.85rem; font-weight:600; color:{GRIS}; background:#fff; }}
.st-key-paso_1_activo button::before, .st-key-paso_1_pend button::before {{ content:"1"; }}
.st-key-paso_2_activo button::before, .st-key-paso_2_pend button::before {{ content:"2"; }}
.st-key-paso_3_activo button::before, .st-key-paso_3_pend button::before {{ content:"3"; }}
[class*="st-key-paso_"][class*="_hecho"] button::before {{ content:"✓"; background:{AZUL_CLARO}; border-color:{AZUL_CLARO}; color:{AZUL}; }}
[class*="st-key-paso_"][class*="_activo"] button::before {{ background:{AZUL}; border-color:{AZUL}; color:#fff; }}
[class*="st-key-paso_"][class*="_activo"] button p {{ color:{TEXTO}; font-weight:700; }}
[class*="st-key-paso_"][class*="_hecho"] button p {{ color:{AZUL}; font-weight:600; }}
[class*="st-key-paso_"][class*="_hecho"] button:hover p, [class*="st-key-paso_"][class*="_pend"] button:not(:disabled):hover p {{
  text-decoration:underline; text-underline-offset:3px; }}
[class*="st-key-paso_"] button:disabled {{ opacity:.55; cursor:not-allowed; }}
[class*="st-key-paso_"][class*="_activo"] button:disabled {{ opacity:1; cursor:default; }}

/* Tarjeta blanca principal */
.st-key-tarjeta {{ background:#fff; border-radius:22px !important; padding:2rem 2.2rem !important;
  box-shadow:0 1px 2px rgba(31,42,36,.04); }}

/* Recuadro del presupuesto */
.st-key-caja_presupuesto {{ background:#EEF5F1; border:1px solid #DCEAE2; border-radius:16px;
  padding:1.4rem 1.6rem 1.6rem; }}
.st-key-caja_presupuesto h4 {{ font-size:1.12rem; font-weight:700; margin:0; padding:0; color:{TEXTO}; }}
.st-key-w_pres input {{ font-size:2.5rem !important; font-weight:700 !important; color:{TEXTO} !important;
  height:4.2rem !important; padding-left:.4rem !important; }}
.st-key-caja_presupuesto [data-testid="stHorizontalBlock"] {{ background:#fff; border:1.5px solid #D3E4DA;
  border-radius:14px; padding:.35rem 1.3rem; align-items:center; box-shadow:0 1px 2px rgba(14,90,67,.06); }}
.st-key-w_pres [data-baseweb="input"], .st-key-w_pres [data-testid="stNumberInputContainer"] {{
  border:none !important; background:transparent !important; box-shadow:none !important; }}
.cn-signo {{ font-size:2.3rem; font-weight:600; color:{AZUL}; text-align:right; }}
/* sin botones + y − en los números */
.stNumberInput button {{ display:none !important; }}
.cn-moneda {{ color:{GRIS}; font-size:.92rem; line-height:1.25; }}

/* Campos y botones */
[data-testid="stWidgetLabel"] p {{ font-weight:600; font-size:1.02rem; color:{TEXTO}; }}
.st-key-nav_on button [data-testid="stIconMaterial"], [class*="st-key-nav_off"] button [data-testid="stIconMaterial"] {{
  font-size:1.35rem; }}
.stTextInput input, .stNumberInput input {{ min-height:2.9rem; }}
[data-testid="stTextInputRootElement"], .stTextInput [data-baseweb="input"], .stNumberInput [data-baseweb="input"],
.stNumberInput [data-testid="stNumberInputContainer"], .stMultiSelect [data-baseweb="select"] > div {{
  background:#fff !important; }}
.stNumberInput button {{ background:#fff !important; }}
[data-testid="stFormSubmitButton"] button, .stButton button[kind="primary"] {{
  min-height:3.4rem; }}
[data-testid="stFormSubmitButton"] button p, .stButton button[kind="primary"] p {{
  font-size:1.08rem; font-weight:700; }}
.cn-pie-paso {{ text-align:center; color:{GRIS}; font-size:.85rem; margin-top:.6rem; }}

/* Menú lateral */
.cn-menu-ceja {{ font-size:.74rem; letter-spacing:.17em; white-space:nowrap; font-weight:700; color:{GRIS};
  text-transform:uppercase; margin:.6rem 0 1rem .2rem; }}
.st-key-nav_on button, [class*="st-key-nav_off"] button {{ justify-content:flex-start; border:none;
  padding:1rem 1.2rem; min-height:3.4rem; font-size:1.02rem; border-radius:14px; }}
.st-key-nav_on button {{ background:{AZUL_CLARO}; color:{TEXTO}; }}
.st-key-nav_on button p, [class*="st-key-nav_off"] button p {{ font-size:1.05rem; }}
.st-key-nav_on button p {{ font-weight:700; }}
[class*="st-key-nav_off"] button {{ background:transparent; color:#56605A; }}
[class*="st-key-nav_off"] button:hover {{ background:#E9F2ED; color:{TEXTO}; }}
.st-key-nav_on button div, [class*="st-key-nav_off"] button div {{ justify-content:flex-start; }}
.cn-menu-nota b {{ display:block; color:{TEXTO}; margin-bottom:.5rem; font-size:1rem; }}
.cn-menu-nota {{ color:{GRIS}; font-size:.95rem; line-height:1.75; padding:0 .2rem; }}

/* Celular */
@media (max-width: 640px) {{
  .cn-lema {{ display:none; }}
  .cn-cabecera {{ margin-bottom:1.4rem; }}
  [class*="st-key-paso_"]:not([class*="_activo"]) button p {{ display:none; }}
  .st-key-pasos [data-testid="stColumn"] {{ width:auto !important; flex:1 1 auto !important; }}
  .st-key-tarjeta {{ padding:1.3rem 1.1rem !important; }}
  .st-key-w_pres input {{ font-size:2rem !important; }}
  .cn-menu-nota, .cn-menu-ceja, .st-key-menu hr, .st-key-menu [data-testid="stCaptionContainer"] {{ display:none; }}
  .st-key-menu_botones {{ flex-direction:row !important; gap:.5rem; }}
  .st-key-menu_botones > div {{ flex:1 1 0 !important; min-width:0; }}
  .st-key-menu [data-testid="stElementContainer"]:has(hr),
  .st-key-menu [data-testid="stElementContainer"]:has(.cn-menu-nota),
  .st-key-menu [data-testid="stElementContainer"]:has(.cn-menu-ceja),
  .st-key-menu [data-testid="stElementContainer"]:has([data-testid="stCaptionContainer"]) {{ display:none; }}
  .st-key-caja_presupuesto [data-testid="stHorizontalBlock"] {{ flex-direction:row !important;
    flex-wrap:nowrap !important; gap:.4rem; }}
  .st-key-caja_presupuesto [data-testid="stColumn"] {{ min-width:0 !important; width:auto !important; }}
  .st-key-caja_presupuesto [data-testid="stColumn"]:nth-child(2) {{ flex:1 1 auto !important; }}
  .st-key-caja_presupuesto [data-testid="stColumn"]:not(:nth-child(2)) {{ flex:0 0 auto !important; }}
  .cn-moneda {{ font-size:.8rem; }}
  .st-key-caja_presupuesto [data-testid="stHorizontalBlock"] {{ padding:.25rem .8rem; }}
  .st-key-caja_presupuesto {{ padding:1.1rem 1rem 1.2rem; }}
  .st-key-nav_on button, [class*="st-key-nav_off"] button {{ min-height:2.8rem; padding:.5rem .7rem; }}
  .st-key-nav_on button p, [class*="st-key-nav_off"] button p {{ font-size:.86rem; white-space:nowrap; }}
  .st-key-nav_on button, [class*="st-key-nav_off"] button {{ padding:.5rem .55rem; gap:.3rem; }}
  .cn-signo {{ font-size:1.8rem; }}
}}
</style>
"""

NOTAS_MENU = {
    1: ("Empieza por lo que tienes.",
        "Tu presupuesto y el tamaño de tu familia son el punto de partida para organizar tus compras."),
    2: ("Compara antes de salir.",
        "Mira qué tienda cercana te conviene para lo que más compras."),
    3: ("Tu dinero, mejor usado.",
        "Una lista realista para todo el mes, y lo que sobra queda como ahorro."),
    "recetas": ("Nada se desperdicia.",
                "Cocina rico y nutritivo con lo que ya tienes en la cocina."),
}


def aplicar_estilos():
    st.markdown(CSS, unsafe_allow_html=True)


def cabecera():
    st.markdown(
        f"""<div class="cn-cabecera">
          <div class="cn-logo"><span class="icono">{ICONO_CANASTA}</span>
            <span class="nombre">canastas<span class="punto"> .</span></span></div>
          <div class="cn-lema">Un buen plan para tu mesa.</div>
        </div>""",
        unsafe_allow_html=True,
    )


def titulo(ceja: str, texto: str, sub: str = ""):
    html = f'<p class="cn-ceja">{ceja}</p><h1 class="cn-titulo">{texto}</h1>'
    if sub:
        html += f'<p class="cn-sub">{sub}</p>'
    st.markdown(html, unsafe_allow_html=True)


def pasos(activo: int, ir=None, habilitados=(1,)):
    """Indicador de pasos; cada paso es un botón para ir directo a él."""
    nombres = ["Tus datos", "Tus tiendas", "Tu canasta"]
    with st.container(key="pasos"):
        cols = st.columns([1.15, 1, 1.25, 1, 1.25], vertical_alignment="center", gap="small")
        for i, nombre in enumerate(nombres, 1):
            estado = "activo" if i == activo else ("hecho" if i < activo else "pend")
            with cols[(i - 1) * 2]:
                with st.container(key=f"paso_{i}_{estado}"):
                    st.button(nombre, key=f"ir_paso_{i}", on_click=ir, args=(i,),
                              disabled=(ir is None or (i not in habilitados and i != activo)),
                              help=None if i == activo else f"Ir a: {nombre}")
            if i < 3:
                cols[i * 2 - 1].markdown('<div class="cn-linea"></div>', unsafe_allow_html=True)


def pie_paso(texto: str):
    st.markdown(f'<p class="cn-pie-paso">{texto}</p>', unsafe_allow_html=True)


def menu(activo, ir):
    """Menú de la izquierda; en el celular queda arriba y compacto."""
    with st.container(key="menu"):
        st.markdown('<p class="cn-menu-ceja">Tu hogar, organizado</p>', unsafe_allow_html=True)
        en_compra = activo in (1, 2, 3)
        with st.container(key="menu_botones"):
            with st.container(key="nav_on" if en_compra else "nav_off_compra"):
                st.button("Mi compra del mes", icon=":material/shopping_basket:", on_click=ir, args=(1,),
                          width="stretch")
            with st.container(key="nav_on" if not en_compra else "nav_off_recetas"):
                st.button("¿Qué cocino hoy?", icon=":material/ramen_dining:", on_click=ir, args=("recetas",),
                          width="stretch")
        st.divider()
        fuerte, texto = NOTAS_MENU.get(activo, NOTAS_MENU[1])
        st.markdown(f'<div class="cn-menu-nota"><b>{fuerte}</b>{texto}</div>', unsafe_allow_html=True)
        st.caption("Precios estimados por IA: confírmalos en la tienda. "
                   "No escribas datos personales; lo que ingresas se envía a la IA de Google.")
