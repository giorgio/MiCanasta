"""Tiendas cercanas (OpenStreetMap) y enlaces para ver el precio actual.

Todo es gratuito y no necesita clave:
- Nominatim convierte "Balao, Guayas" en coordenadas.
- Overpass busca supermercados, mercados y tiendas alrededor de un punto.
Ambos servicios piden identificarse con un User-Agent y no abusar de ellos,
por eso los resultados se guardan en caché.
"""

from __future__ import annotations

import math
from urllib.parse import quote_plus

import requests

USER_AGENT = "CanastaInteligente/1.0 (proyecto academico ESPOL; app Streamlit)"
NOMINATIM = "https://nominatim.openstreetmap.org/search"
OVERPASS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]

# Cadenas de Ecuador: nombre que mostramos -> palabras con las que aparecen en el mapa
CADENAS = {
    "Tía": ["tia", "tía", "almacenes tia"],
    "Mi Comisariato": ["mi comisariato", "comisariato"],
    "Supermaxi": ["supermaxi"],
    "Akí / Gran Akí": ["aki", "akí", "gran aki", "gran akí", "super aki"],
    "Santa María": ["santa maria", "santa maría", "supermercados santa maria"],
    "Coral Hipermercados": ["coral", "coral hipermercados"],
    "TuTi": ["tuti", "tu ti"],
    "Megamaxi": ["megamaxi"],
    "Hipermarket": ["hipermarket"],
}

TIPOS = {
    "supermarket": "Supermercado",
    "convenience": "Tienda de barrio",
    "greengrocer": "Frutas y verduras",
    "butcher": "Carnicería",
    "marketplace": "Mercado",
}

# Páginas de búsqueda de cada cadena. Solo se usan como ENLACES que abre la
# persona en su navegador; la app no lee esas páginas automáticamente.
BUSQUEDA_TIENDA = {
    "Tía": "https://www.tia.com.ec/catalogsearch/result/?q={q}",
}
NO_ONLINE = {"Mercado municipal", "Feria libre", "Tienda de barrio", "Mercado mayorista"}


class ErrorMapa(Exception):
    pass


def distancia_km(lat1, lon1, lat2, lon2) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def cadena_de(nombre: str, marca: str = "") -> str | None:
    texto = f" {nombre} {marca} ".lower()
    for cadena, claves in CADENAS.items():
        for c in claves:
            if f" {c} " in texto or texto.strip().startswith(c):
                return cadena
    return None


def geocodificar(lugar: str) -> tuple[float, float, str]:
    """Devuelve (lat, lon, nombre legible) de un lugar de Ecuador."""
    datos = []
    # Primero buscamos un pueblo o ciudad (no el cantón entero), luego cualquier lugar.
    for extra in ({"featureType": "settlement"}, {}):
        try:
            r = requests.get(
                NOMINATIM,
                params={"q": lugar, "format": "json", "limit": 1, "countrycodes": "ec", **extra},
                headers={"User-Agent": USER_AGENT},
                timeout=15,
            )
            r.raise_for_status()
            datos = r.json()
        except requests.RequestException as e:
            raise ErrorMapa("No se pudo consultar el mapa en este momento. Intenta de nuevo en un minuto.") from e
        if datos:
            break
    if not datos:
        raise ErrorMapa(f"No encontré '{lugar}' en Ecuador. Prueba con 'ciudad, provincia', por ejemplo 'Balao, Guayas'.")
    d = datos[0]
    return float(d["lat"]), float(d["lon"]), d.get("display_name", lugar)


def _consulta(lat: float, lon: float, radio_m: int) -> str:
    alrededor = f"around:{radio_m},{lat},{lon}"
    return (
        "[out:json][timeout:25];("
        f'nwr({alrededor})["shop"~"^(supermarket|convenience|greengrocer|butcher)$"];'
        f'nwr({alrededor})["amenity"="marketplace"];'
        ");out center 200;"
    )


def tiendas_cercanas(lat: float, lon: float, radio_km: float = 5) -> list[dict]:
    """Lista de tiendas reales cerca del punto, ordenadas por distancia."""
    consulta = _consulta(lat, lon, int(radio_km * 1000))
    ultimo = None
    for url in OVERPASS:
        try:
            r = requests.post(url, data={"data": consulta}, headers={"User-Agent": USER_AGENT}, timeout=30)
            r.raise_for_status()
            elementos = r.json().get("elements", [])
            break
        except (requests.RequestException, ValueError) as e:
            ultimo = e
    else:
        raise ErrorMapa("El servicio de mapas no respondió. Puedes seguir eligiendo tus tiendas a mano.") from ultimo

    tiendas = []
    for el in elementos:
        tags = el.get("tags", {})
        la = el.get("lat") or el.get("center", {}).get("lat")
        lo = el.get("lon") or el.get("center", {}).get("lon")
        if la is None or lo is None:
            continue
        tipo_osm = tags.get("shop") or tags.get("amenity")
        nombre = tags.get("name") or tags.get("brand") or TIPOS.get(tipo_osm, "Tienda")
        cadena = cadena_de(nombre, tags.get("brand", ""))
        tiendas.append({
            "nombre": nombre,
            "tipo": TIPOS.get(tipo_osm, "Tienda"),
            "cadena": cadena,
            "lat": float(la),
            "lon": float(lo),
            "distancia_km": round(distancia_km(lat, lon, float(la), float(lo)), 2),
            "direccion": " ".join(filter(None, [tags.get("addr:street"), tags.get("addr:housenumber")])),
        })
    tiendas.sort(key=lambda t: t["distancia_km"])
    return tiendas


def tiendas_para_plan(tiendas: list[dict]) -> list[str]:
    """Convierte lo que hay cerca en las opciones de tienda del formulario."""
    opciones = []
    for t in tiendas:
        if t["cadena"]:
            op = t["cadena"]
        elif t["tipo"] == "Mercado" and "mayorista" in t["nombre"].lower():
            op = "Mercado mayorista"
        elif t["tipo"] == "Mercado":
            op = "Mercado municipal"
        elif t["tipo"] in ("Tienda de barrio", "Frutas y verduras", "Carnicería"):
            op = "Tienda de barrio"
        else:
            continue
        if op not in opciones:
            opciones.append(op)
    return opciones


def resumen_cercanas(tiendas: list[dict], maximo: int = 8) -> str:
    """Texto corto para incluir en el prompt."""
    partes = []
    for t in tiendas[:maximo]:
        partes.append(f"{t['nombre']} ({t['tipo']}, {t['distancia_km']} km)")
    return "; ".join(partes) if partes else "desconocidas"


def enlace_precio(producto: str, tienda: str) -> str:
    """Enlace para que la persona vea el precio de hoy de ese producto."""
    if tienda in BUSQUEDA_TIENDA:
        return BUSQUEDA_TIENDA[tienda].format(q=quote_plus(producto))
    if tienda in NO_ONLINE:
        return "https://www.google.com/search?q=" + quote_plus(f"precio {producto} mercado Ecuador hoy")
    return "https://www.google.com/search?q=" + quote_plus(f"{producto} precio {tienda} Ecuador")


def enlace_mapa(lat: float, lon: float, nombre: str) -> str:
    return f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
