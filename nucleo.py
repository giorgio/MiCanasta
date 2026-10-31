"""Lógica de la app Canastas (sin interfaz).

Aquí viven los modelos de datos, los prompts, la llamada a Gemini,
las validaciones y los cálculos. app.py solo dibuja la interfaz.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------

MODELO_PRINCIPAL = "gemini-3.8-flash"
MODELO_RESPALDO = "gemini-3.5-flash-lite"

TIENDAS_DISPONIBLES = [
    "Mercado municipal",
    "Feria libre",
    "Tienda de barrio",
    "Tía",
    "Mi Comisariato",
    "Supermaxi",
    "Akí / Gran Akí",
    "Santa María",
    "Coral Hipermercados",
    "TuTi",
    "Megamaxi",
    "Hipermarket",
    "Mercado mayorista",
]

# Por debajo de este monto por persona y por día el plan será muy ajustado.
MINIMO_DIARIO_RECOMENDADO = 1.50  # USD
LIMITE_PRESUPUESTO = 5000  # USD al mes, para detectar errores de tipeo


# ---------------------------------------------------------------------------
# Esquemas de salida (Gemini responde en JSON con esta forma exacta)
# ---------------------------------------------------------------------------

class ItemCompra(BaseModel):
    producto: str = Field(description="Nombre del producto, p. ej. 'Arroz'")
    categoria: str = Field(description="Granos y cereales, Proteínas, Frutas y verduras, Lácteos, Despensa u Otros")
    cantidad: float = Field(description="Cantidad total para el mes")
    unidad: str = Field(description="Unidad de la cantidad: kg, lb, litro, unidad, docena, funda...")
    tienda: str = Field(description="Una de las tiendas elegidas por el usuario")
    precio_unitario_usd: float = Field(description="Precio estimado en USD por UNA unidad de 'unidad'")
    motivo: str = Field(description="Por qué conviene comprarlo en esa tienda, en una frase")


class ComidaDia(BaseModel):
    dia: str
    desayuno: str
    almuerzo: str
    merienda: str


class PlanCompras(BaseModel):
    resumen: str = Field(description="Dos o tres frases que expliquen la estrategia del plan")
    items: list[ItemCompra]
    menu_semana_ejemplo: list[ComidaDia] = Field(description="Siete días de ejemplo usando solo lo comprado")
    consejos: list[str] = Field(description="De 3 a 5 consejos concretos para ahorrar")


class Receta(BaseModel):
    nombre: str
    porciones: int
    tiempo_minutos: int
    ingredientes_que_tienes: list[str]
    ingredientes_faltantes: list[str] = Field(description="Vacío si no falta nada; solo cosas baratas")
    costo_faltantes_usd: float
    pasos: list[str]
    por_que_es_nutritiva: str
    calorias_aprox_por_porcion: int
    proteina_g_aprox_por_porcion: int


class RecetaSemana(BaseModel):
    semana: int = Field(description="1, 2, 3 o 4")
    receta: Receta


class Recetario(BaseModel):
    semanas: list[RecetaSemana]


class RespuestaRecetas(BaseModel):
    recetas: list[Receta]
    aviso: str = Field(description="Vacío, o una advertencia si los ingredientes no alcanzan o no son comida")


class PrecioTienda(BaseModel):
    tienda: str
    precio_usd: float = Field(description="Precio estimado en USD de la presentación indicada; 0 si esa tienda no suele venderlo")


class FilaComparacion(BaseModel):
    producto: str
    presentacion: str = Field(description="Presentación común en Ecuador, p. ej. 'funda 2 kg', 'cubeta 30 unidades', 'litro'")
    precios: list[PrecioTienda]


class Comparacion(BaseModel):
    filas: list[FilaComparacion]
    nota: str = Field(description="Una frase sobre qué tipo de tienda suele ser más barata para estos productos")


# ---------------------------------------------------------------------------
# Prompts (reutilizables: se documentan también en PROMPTS.md)
# ---------------------------------------------------------------------------

SISTEMA = (
    "Eres un asistente de economía doméstica y nutrición para hogares de Ecuador. "
    "Trabajas en dólares (USD) y conoces los precios habituales de mercados, ferias "
    "y supermercados ecuatorianos. Tus precios son ESTIMACIONES, nunca afirmes que "
    "son exactos. Priorizas comida nutritiva, sencilla y típica de la zona (arroz, "
    "menestras, verde, yuca, huevos, pollo, pescado, atún, frutas y verduras de "
    "temporada). No das consejos médicos. Respondes siempre en español neutro."
)

PROMPT_PLAN = """Arma la lista de compras de UN MES para este hogar.

DATOS DEL HOGAR
- Presupuesto mensual para comida: {presupuesto:.2f} USD
- Personas: {personas}
- Comidas al día: {comidas}
- Ciudad o zona: {ciudad}
- Tiendas a las que puede ir (usa SOLO estas): {tiendas}
- Tiendas reales cerca de su casa (OpenStreetMap): {cercanas}
- Preferencias o restricciones: {restricciones}
- Ya tiene en casa (no lo compres de nuevo): {en_casa}
- Precios que el usuario ya conoce (respétalos): {precios_conocidos}

REGLAS
1. La suma de cantidad x precio_unitario_usd de todos los productos debe ser
   MENOR O IGUAL a {presupuesto:.2f} USD. NO hace falta gastar todo: si sobra dinero,
   déjalo como ahorro. NUNCA aumentes cantidades para llegar al presupuesto.
2. Cantidades REALISTAS para {personas} persona(s) durante 30 días, según esta guía
   de consumo típico POR PERSONA AL MES (multiplícala por {personas}):
   arroz 4-6 kg; aceite 0,5-0,8 litros; azúcar 0,5-1 kg; sal 0,25 kg; huevos 20-30;
   pollo, carne y pescado 3-5 kg en total; atún 4-6 latas; menestras 1-2 kg;
   leche 4-8 litros; verde, yuca y papa 4-6 kg en total; frutas 4-6 kg;
   verduras 4-6 kg; pan 2-4 kg; avena 0,5-1 kg; fideo 1-2 kg.
3. Asigna cada producto a la tienda más barata para ese tipo de producto
   (por lo general: frutas, verduras y proteína fresca en mercado o feria; granos,
   aceite y productos empacados en supermercado o al por mayor). Si una tienda
   está mucho más cerca, prefiérela cuando la diferencia de precio sea pequeña.
4. precio_unitario_usd es el precio de UNA unidad de la columna 'unidad'.
5. Cubre todos los grupos: energía (granos, tubérculos), proteína, frutas y verduras.
6. Entre 12 y 22 productos. Nada de comida chatarra ni bebidas azucaradas.
7. 'motivo' y los consejos: frases MUY cortas (máximo 12 palabras).
{correccion}"""

PROMPT_RECETAS = """Propón 3 recetas nutritivas que se puedan preparar con lo que hay en casa.

INGREDIENTES DISPONIBLES: {ingredientes}
PERSONAS: {personas}
PREFERENCIAS O RESTRICCIONES: {restricciones}

REGLAS
1. Usa principalmente los ingredientes disponibles. Puedes asumir que hay sal,
   agua y aceite.
2. Si falta algo, que sea barato (menos de 2 USD en total por receta) y
   anótalo en ingredientes_faltantes con su costo aproximado.
3. Pasos cortos y claros, pensados para alguien que cocina poco.
4. Calorías y proteína son aproximadas por porción.
5. Si los ingredientes no alcanzan para ninguna receta, o no son alimentos,
   devuelve la lista de recetas vacía y explica el motivo en 'aviso'."""


PROMPT_COMPARAR = """Compara el precio ESTIMADO de estos productos en estas tiendas de Ecuador.

PRODUCTOS: {productos}
TIENDAS: {tiendas}
CIUDAD O ZONA: {ciudad}
PRECIOS QUE EL USUARIO YA VIO (úsalos tal cual para esa tienda): {precios_conocidos}

REGLAS
1. Una fila por producto, con la MISMA presentación para todas las tiendas, para que sean comparables.
2. En cada fila incluye TODAS las tiendas de la lista, con el nombre exacto.
3. Precios en USD, realistas para Ecuador hoy. Si una tienda no suele vender ese producto, pon 0.
4. Mercados, ferias y mayoristas suelen ser más baratos en frescos; las cadenas, en empacados y ofertas."""

PRODUCTOS_COMUNES = [
    "Arroz", "Aceite", "Azúcar", "Huevos", "Pollo entero", "Atún en lata", "Leche",
    "Lenteja", "Fréjol", "Verde", "Papa", "Cebolla paiteña", "Tomate", "Queso fresco",
    "Pan", "Avena", "Pescado", "Carne de res", "Plátano maduro", "Fideo",
]
MAX_PRODUCTOS_COMPARAR = 15


PROMPT_RECETARIO = """Crea 4 recetas saludables, UNA POR SEMANA del mes, para este hogar.

INGREDIENTES QUE COMPRÓ PARA EL MES: {ingredientes}
PERSONAS: {personas}
PREFERENCIAS O RESTRICCIONES: {restricciones}

REGLAS
1. Usa solo esos ingredientes (puedes asumir sal, agua, aceite y condimentos básicos).
   ingredientes_faltantes debe ir vacío y costo_faltantes_usd en 0.
2. Las 4 recetas deben ser distintas entre sí y equilibradas: proteína, verduras o frutas, y algo de energía.
3. Platos caseros de Ecuador, sencillos, de máximo 60 minutos. Pasos cortos (máximo 7).
4. porciones = {personas}."""


# ---------------------------------------------------------------------------
# Validación de entradas (antes de gastar una consulta a la IA)
# ---------------------------------------------------------------------------

@dataclass
class Validacion:
    errores: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errores


def validar_plan(presupuesto: float, personas: int, tiendas: list[str]) -> Validacion:
    v = Validacion()
    if presupuesto is None or presupuesto <= 0:
        v.errores.append("Escribe un presupuesto mayor que 0 USD.")
    elif presupuesto > LIMITE_PRESUPUESTO:
        v.errores.append(
            f"Un presupuesto de {presupuesto:,.2f} USD al mes parece un error de tipeo. "
            f"El máximo permitido es {LIMITE_PRESUPUESTO:,} USD."
        )
    if personas is None or personas < 1:
        v.errores.append("Indica al menos 1 persona.")
    if not tiendas:
        v.errores.append("Elige al menos una tienda donde puedas comprar.")
    if v.ok:
        diario = por_persona_por_dia(presupuesto, personas)
        if diario < MINIMO_DIARIO_RECOMENDADO:
            v.avisos.append(
                f"Tu presupuesto equivale a {diario:.2f} USD por persona al día. Es muy "
                "ajustado: el plan priorizará lo básico y puede quedarse corto en variedad."
            )
    return v


def validar_recetas(ingredientes: str) -> Validacion:
    v = Validacion()
    texto = (ingredientes or "").strip()
    if not texto:
        v.errores.append("Escribe al menos un ingrediente que tengas en casa.")
    elif len(separar_lista(texto)) < 2:
        v.avisos.append("Con un solo ingrediente las recetas serán muy limitadas; agrega más si puedes.")
    if len(texto) > 1500:
        v.errores.append("La lista es demasiado larga. Resúmela en menos de 1500 caracteres.")
    return v


def separar_lista(texto: str) -> list[str]:
    partes = texto.replace("\n", ",").replace(";", ",").split(",")
    return [p.strip() for p in partes if p.strip()]


def por_persona_por_dia(presupuesto: float, personas: int) -> float:
    return presupuesto / (max(personas, 1) * 30)


# ---------------------------------------------------------------------------
# Cálculos sobre la respuesta (no confiamos en la suma que haga la IA)
# ---------------------------------------------------------------------------

def limpiar_items(items: list[ItemCompra], tiendas: list[str]) -> tuple[list[ItemCompra], list[str]]:
    """Quita productos con datos imposibles y marca tiendas no elegidas."""
    limpios, avisos = [], []
    for it in items:
        if it.cantidad <= 0 or it.precio_unitario_usd <= 0:
            avisos.append(f"Se descartó '{it.producto}' porque venía sin cantidad o sin precio.")
            continue
        if it.tienda not in tiendas:
            avisos.append(f"'{it.producto}' venía asignado a '{it.tienda}', que no elegiste; revisa dónde comprarlo.")
        limpios.append(it)
    return limpios, avisos


def subtotal(it: ItemCompra) -> float:
    return round(it.cantidad * it.precio_unitario_usd, 2)


def total_plan(items: list[ItemCompra]) -> float:
    return round(sum(subtotal(i) for i in items), 2)


def totales_por_tienda(items: list[ItemCompra]) -> dict[str, float]:
    out: dict[str, float] = {}
    for it in items:
        out[it.tienda] = round(out.get(it.tienda, 0) + subtotal(it), 2)
    return dict(sorted(out.items(), key=lambda kv: -kv[1]))


def tabla_items(items: list[ItemCompra]) -> list[dict]:
    filas = []
    for it in sorted(items, key=lambda i: (i.tienda, i.categoria, i.producto)):
        filas.append({
            "Tienda": it.tienda,
            "Producto": it.producto,
            "Categoría": it.categoria,
            "Cantidad": f"{it.cantidad:g} {it.unidad}",
            "Precio unit. (USD)": round(it.precio_unitario_usd, 2),
            "Subtotal (USD)": subtotal(it),
            "Por qué ahí": it.motivo,
        })
    return filas


# Consumo máximo razonable por persona al mes (palabra clave -> (cantidad, "kg" | "l" | "u")).
TOPE_POR_PERSONA = {
    "aceite": (0.8, "l"), "arroz": (6, "kg"), "azúcar": (1, "kg"), "azucar": (1, "kg"), "sal": (0.25, "kg"),
    "huevo": (30, "u"), "leche": (8, "l"), "avena": (1, "kg"), "fideo": (2, "kg"), "lenteja": (2, "kg"),
    "fréjol": (2, "kg"), "frejol": (2, "kg"), "atún": (6, "u"), "atun": (6, "u"), "pan": (4, "kg"),
}
_FACTOR = {"kg": ("kg", 1), "kilo": ("kg", 1), "lb": ("kg", 0.4536), "libra": ("kg", 0.4536),
           "g": ("kg", 0.001), "gr": ("kg", 0.001), "l": ("l", 1), "litro": ("l", 1), "ml": ("l", 0.001),
           "cubeta": ("u", 30), "docena": ("u", 12), "lata": ("u", 1), "unidad": ("u", 1), "unidades": ("u", 1)}


def _por_unidad(unidad: str, dim: str = "") -> tuple[str, float] | None:
    """'botella 900 ml' -> ('l', 0.9); 'funda 2 kg' -> ('kg', 2); 'lata 140 g' con dim 'u' -> ('u', 1)."""
    import re

    texto = unidad.lower().replace(",", ".")
    if dim == "u":  # se cuenta por piezas: lata, cubeta, docena…
        for palabra, (d, f) in _FACTOR.items():
            if d == "u" and re.search(rf"\b{palabra}s?\b", texto):
                return d, f
    m = re.search(r"(\d+(?:\.\d+)?)\s*(kg|kilo|lb|libra|gr|g|ml|litro|l)\b", texto)
    if m:
        dim, f = _FACTOR[m.group(2)]
        return dim, float(m.group(1)) * f
    for palabra, (dim, f) in _FACTOR.items():
        if re.search(rf"\b{palabra}s?\b", texto):
            return dim, f
    return None


def ajustar_cantidades(items: list[ItemCompra], personas: int) -> list[str]:
    """Baja las cantidades exageradas al consumo máximo razonable. Devuelve avisos."""
    import math

    avisos = []
    for it in items:
        nombre = it.producto.lower()
        clave = next((k for k in TOPE_POR_PERSONA if k in nombre), None)
        if not clave:
            continue
        tope, dim = TOPE_POR_PERSONA[clave]
        conv = _por_unidad(it.unidad, dim)
        if not conv:
            continue
        dim_item, por_unidad = conv
        if dim_item != dim or por_unidad <= 0:
            continue
        maximo = tope * max(personas, 1)
        if it.cantidad * por_unidad > maximo * 1.15:
            nueva = max(1, math.ceil(maximo / por_unidad - 1e-9))
            if nueva < it.cantidad:
                avisos.append(f"Ajusté {it.producto}: de {it.cantidad:g} a {nueva:g} {it.unidad}, "
                              f"suficiente para {personas} persona(s) al mes.")
                it.cantidad = nueva
    return avisos


# ---------------------------------------------------------------------------
# Llamada a Gemini con manejo de errores y cuotas
# ---------------------------------------------------------------------------

class ErrorIA(Exception):
    """Error con un mensaje ya listo para mostrar al usuario."""


def _codigo(e: Exception) -> int | None:
    return getattr(e, "code", None) or getattr(e, "status_code", None)


def llamar_gemini(cliente, prompt: str, esquema, modelos=(MODELO_PRINCIPAL, MODELO_RESPALDO), reintentos: int = 1,
                  razonamiento: str = "low"):
    """Pide JSON con 'esquema'. Si el modelo principal no tiene cuota o no existe,
    prueba con el de respaldo. Devuelve (objeto, modelo_usado)."""
    from google.genai import types  # import aquí para poder probar sin la librería

    ultimo_error: Exception | None = None
    usar_nivel = True
    for modelo in modelos:
        for intento in range(reintentos + 1):
            try:
                resp = cliente.models.generate_content(
                    model=modelo,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=SISTEMA,
                        response_mime_type="application/json",
                        response_schema=esquema,
                        temperature=0.4,
                        max_output_tokens=12000,
                        thinking_config=types.ThinkingConfig(thinking_level=razonamiento) if usar_nivel else None,
                    ),
                )
                obj = resp.parsed
                if obj is None and getattr(resp, "text", None):
                    obj = esquema.model_validate(json.loads(resp.text))
                if obj is None:
                    raise ValueError("respuesta vacía")
                return obj, modelo
            except Exception as e:  # noqa: BLE001
                ultimo_error = e
                codigo = _codigo(e)
                if codigo in (401, 403):
                    raise ErrorIA(
                        "La clave de la API de Gemini no es válida o no tiene permiso. "
                        "Revisa el secreto GEMINI_API_KEY en la configuración de la app."
                    ) from e
                if codigo == 400 and usar_nivel and "think" in str(e).lower():
                    usar_nivel = False  # el modelo no acepta ese nivel: reintentar sin él
                    continue
                if codigo in (404, 429):
                    break  # este modelo no está disponible o no tiene cuota: probar el siguiente
                if intento < reintentos:
                    time.sleep(2)
                    continue
                break

    codigo = _codigo(ultimo_error) if ultimo_error else None
    if codigo == 429:
        raise ErrorIA(
            "Se alcanzó el límite gratuito de consultas a la IA. Espera un minuto y "
            "vuelve a intentar. Si sigue pasando, el límite diario se reinicia a medianoche "
            "(hora del Pacífico, 3 a. m. en Ecuador)."
        )
    if codigo and codigo >= 500:
        raise ErrorIA("El servicio de IA de Google está saturado en este momento. Intenta de nuevo en unos minutos.")
    raise ErrorIA(
        "La IA no devolvió una respuesta válida. Intenta de nuevo; si se repite, "
        "simplifica lo que escribiste en preferencias o ingredientes."
    )


def generar_plan(cliente, presupuesto, personas, comidas, ciudad, tiendas, restricciones, en_casa, precios_conocidos, cercanas=""):
    """Genera el plan y, si se pasa del presupuesto, pide UNA corrección automática."""
    datos = dict(
        presupuesto=presupuesto,
        personas=personas,
        comidas=comidas,
        ciudad=ciudad or "Guayaquil, Ecuador",
        tiendas=", ".join(tiendas),
        restricciones=restricciones or "ninguna",
        en_casa=en_casa or "nada",
        precios_conocidos=precios_conocidos or "ninguno",
        cercanas=cercanas or "desconocidas",
    )
    plan, modelo = llamar_gemini(cliente, PROMPT_PLAN.format(correccion="", **datos), PlanCompras)
    items, avisos = limpiar_items(plan.items, tiendas)
    total = total_plan(items)
    corregido = False

    if total > presupuesto:
        correccion = (
            f"\nCORRECCIÓN OBLIGATORIA: tu propuesta anterior costaba {total:.2f} USD y el "
            f"presupuesto es {presupuesto:.2f} USD. Reduce cantidades o cambia por productos "
            "más baratos hasta quedar dentro del presupuesto."
        )
        plan2, modelo = llamar_gemini(cliente, PROMPT_PLAN.format(correccion=correccion, **datos), PlanCompras)
        items2, avisos2 = limpiar_items(plan2.items, tiendas)
        if total_plan(items2) <= total:  # nos quedamos con la versión más barata
            plan, items, avisos, total = plan2, items2, avisos2, total_plan(items2)
        corregido = True

    if not items:
        raise ErrorIA("La IA no propuso ningún producto válido. Intenta de nuevo.")

    avisos = ajustar_cantidades(items, personas) + avisos
    total = total_plan(items)

    plan.items = items
    return {
        "plan": plan,
        "total": total,
        "sobrante": round(presupuesto - total, 2),
        "dentro_presupuesto": total <= presupuesto,
        "avisos": avisos,
        "corregido": corregido,
        "modelo": modelo,
    }


def generar_recetas(cliente, ingredientes, personas, restricciones):
    prompt = PROMPT_RECETAS.format(
        ingredientes=", ".join(separar_lista(ingredientes)),
        personas=personas,
        restricciones=restricciones or "ninguna",
    )
    resp, modelo = llamar_gemini(cliente, prompt, RespuestaRecetas, razonamiento="minimal")
    return resp, modelo


def validar_comparacion(productos: list[str], tiendas: list[str]) -> Validacion:
    v = Validacion()
    if not productos:
        v.errores.append("Elige al menos un producto para comparar.")
    if len(productos) > MAX_PRODUCTOS_COMPARAR:
        v.errores.append(f"Compara como máximo {MAX_PRODUCTOS_COMPARAR} productos a la vez.")
    if len(tiendas) < 2:
        v.errores.append("Elige al menos dos tiendas para comparar.")
    return v


def comparar_precios(cliente, productos, tiendas, ciudad="", precios_conocidos=""):
    prompt = PROMPT_COMPARAR.format(
        productos=", ".join(productos), tiendas=", ".join(tiendas),
        ciudad=ciudad or "Guayaquil, Ecuador", precios_conocidos=precios_conocidos or "ninguno",
    )
    comp, modelo = llamar_gemini(cliente, prompt, Comparacion, razonamiento="minimal")
    if not comp.filas:
        raise ErrorIA("La IA no devolvió precios para comparar. Intenta de nuevo.")
    return comp, modelo


def tabla_comparacion(comp: Comparacion, tiendas: list[str]) -> tuple[list[dict], dict[str, float], dict[str, int]]:
    """Filas para mostrar, total por tienda (solo productos que venden todas) y veces que cada tienda es la más barata."""
    filas, totales, ganadas = [], {t: 0.0 for t in tiendas}, {t: 0 for t in tiendas}
    for f in comp.filas:
        precios = {p.tienda: p.precio_usd for p in f.precios if p.tienda in tiendas}
        validos = {t: v for t, v in precios.items() if v and v > 0}
        fila = {"Producto": f.producto, "Presentación": f.presentacion}
        for t in tiendas:
            v = precios.get(t, 0)
            fila[t] = round(v, 2) if v and v > 0 else None
        if validos:
            barata = min(validos, key=validos.get)
            fila["Más barato en"] = barata
            fila["Ahorro vs. más caro"] = round(max(validos.values()) - validos[barata], 2)
            ganadas[barata] += 1
        else:
            fila["Más barato en"] = "—"
            fila["Ahorro vs. más caro"] = None
        if len(validos) == len(tiendas):
            for t in tiendas:
                totales[t] = round(totales[t] + validos[t], 2)
        filas.append(fila)
    return filas, totales, ganadas


def resumen_por_tienda(comp: Comparacion, tiendas: list[str]) -> dict[str, dict]:
    """Por tienda: total de los productos con precio y cuántos tienen precio."""
    out = {t: {"total": 0.0, "con_precio": 0, "productos": len(comp.filas)} for t in tiendas}
    for f in comp.filas:
        for p in f.precios:
            if p.tienda in out and p.precio_usd and p.precio_usd > 0:
                out[p.tienda]["total"] = round(out[p.tienda]["total"] + p.precio_usd, 2)
                out[p.tienda]["con_precio"] += 1
    return out


def tiendas_con_precio(comp: Comparacion, tiendas: list[str]) -> list[str]:
    """Solo las tiendas que tienen precio en al menos un producto, de la más barata a la más cara."""
    res = resumen_por_tienda(comp, tiendas)
    con = [t for t in tiendas if res[t]["con_precio"] > 0]
    return sorted(con, key=lambda t: (-res[t]["con_precio"], res[t]["total"]))


def precios_como_texto(comp: Comparacion, tiendas: list[str]) -> str:
    """Resumen de la comparación para que el plan del mes use los mismos precios."""
    partes = []
    for f in comp.filas:
        ps = [f"{p.tienda} {p.precio_usd:.2f}" for p in f.precios if p.tienda in tiendas and p.precio_usd > 0]
        if ps:
            partes.append(f"{f.producto} ({f.presentacion}): " + ", ".join(ps))
    return "; ".join(partes)


def generar_recetario(cliente, items: list[ItemCompra], personas: int, restricciones: str = ""):
    prompt = PROMPT_RECETARIO.format(
        ingredientes=", ".join(sorted({i.producto for i in items})),
        personas=personas, restricciones=restricciones or "ninguna",
    )
    rec, modelo = llamar_gemini(cliente, prompt, Recetario, razonamiento="minimal")
    semanas = sorted(rec.semanas, key=lambda s: s.semana)[:4]
    if not semanas:
        raise ErrorIA("La IA no devolvió recetas. Intenta de nuevo.")
    for i, s in enumerate(semanas, 1):
        s.semana = i
    rec.semanas = semanas
    return rec, modelo


def _ics_texto(t: str) -> str:
    return t.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def _ics_doblar(linea: str) -> str:
    """Las líneas de un .ics no deben pasar de 75 bytes; se continúan con un espacio."""
    partes, actual = [], ""
    for ch in linea:
        if len((actual + ch).encode("utf-8")) > 74:
            partes.append(actual)
            actual = " " + ch
        else:
            actual += ch
    partes.append(actual)
    return "\r\n".join(partes)


def recetario_ics(rec: Recetario, primer_dia, hora: int = 9) -> str:
    """Calendario con una receta por semana y un recordatorio ese día."""
    from datetime import datetime, timedelta, timezone

    sello = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lineas = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Canastas//Recetario semanal//ES",
              "CALSCALE:GREGORIAN", "METHOD:PUBLISH", "X-WR-CALNAME:Canastas - recetas de la semana"]
    for s in rec.semanas:
        r = s.receta
        dia = primer_dia + timedelta(weeks=s.semana - 1)
        inicio = f"{dia:%Y%m%d}T{hora:02d}0000"
        fin = f"{dia:%Y%m%d}T{hora + 1:02d}0000"
        descripcion = (
            f"{r.nombre} ({r.porciones} porciones, {r.tiempo_minutos} min)\n\n"
            "Ingredientes: " + ", ".join(r.ingredientes_que_tienes) + "\n\nPreparación:\n"
            + "\n".join(f"{i}. {p}" for i, p in enumerate(r.pasos, 1))
            + f"\n\nPor qué es saludable: {r.por_que_es_nutritiva}"
        )
        lineas += [
            "BEGIN:VEVENT", f"UID:canastas-{dia:%Y%m%d}-{s.semana}@canastas.streamlit.app", f"DTSTAMP:{sello}",
            f"DTSTART:{inicio}", f"DTEND:{fin}",
            _ics_doblar("SUMMARY:" + _ics_texto(f"🥗 Receta de la semana {s.semana}: {r.nombre}")),
            _ics_doblar("DESCRIPTION:" + _ics_texto(descripcion)),
            "BEGIN:VALARM", "ACTION:DISPLAY", "TRIGGER:-PT0M",
            _ics_doblar("DESCRIPTION:" + _ics_texto(f"Hoy toca: {r.nombre}")), "END:VALARM", "END:VEVENT",
        ]
    lineas.append("END:VCALENDAR")
    return "\r\n".join(lineas) + "\r\n"


def recetario_texto(rec: Recetario) -> str:
    out = ["CANASTAS - Recetas saludables para cada semana", ""]
    for s in rec.semanas:
        r = s.receta
        out += [f"SEMANA {s.semana}: {r.nombre} ({r.porciones} porciones, {r.tiempo_minutos} min)",
                "Ingredientes: " + ", ".join(r.ingredientes_que_tienes)]
        out += [f"  {i}. {p}" for i, p in enumerate(r.pasos, 1)]
        out += [f"Por qué es saludable: {r.por_que_es_nutritiva}", ""]
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Exportar
# ---------------------------------------------------------------------------

def plan_a_texto(resultado: dict, presupuesto: float) -> str:
    plan: PlanCompras = resultado["plan"]
    lineas = [
        "CANASTAS - Lista de compras del mes",
        f"Presupuesto: {presupuesto:.2f} USD | Total estimado: {resultado['total']:.2f} USD | "
        f"Sobrante: {resultado['sobrante']:.2f} USD",
        "Precios estimados: confírmalos en la tienda.",
        "",
    ]
    tienda_actual = None
    for f in tabla_items(plan.items):
        if f["Tienda"] != tienda_actual:
            tienda_actual = f["Tienda"]
            lineas += ["", f"== {tienda_actual} =="]
        lineas.append(f"[ ] {f['Producto']} - {f['Cantidad']} - {f['Subtotal (USD)']:.2f} USD")
    lineas += ["", "Consejos:"] + [f"- {c}" for c in plan.consejos]
    return "\n".join(lineas)
