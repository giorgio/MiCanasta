"""Pruebas de ubicacion.py sin internet (se simulan las respuestas del mapa)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import ubicacion as u

assert u.cadena_de("Tía Balao") == "Tía"
assert u.cadena_de("Mi Comisariato Naranjal") == "Mi Comisariato"
assert u.cadena_de("Gran Akí") == "Akí / Gran Akí"
assert u.cadena_de("Megamaxi Mall del Sol") == "Megamaxi"
assert u.cadena_de("Coral Hipermercados") == "Coral Hipermercados"
assert u.cadena_de("Tienda Doña Rosa") is None
assert u.cadena_de("Tiendas Industriales", "Tía") == "Tía"
assert 10 < u.distancia_km(-2.19, -79.89, -2.29, -79.89) < 12

class R:
    def __init__(s, j, code=200): s._j, s.status_code = j, code
    def json(s): return s._j
    def raise_for_status(s):
        if s.status_code >= 400: raise u.requests.HTTPError(str(s.status_code))

FAKE = {"elements": [
    {"type": "node", "lat": -2.905, "lon": -79.81, "tags": {"shop": "supermarket", "name": "Tía Balao"}},
    {"type": "way", "center": {"lat": -2.91, "lon": -79.815}, "tags": {"amenity": "marketplace", "name": "Mercado Municipal de Balao"}},
    {"type": "node", "lat": -2.902, "lon": -79.812, "tags": {"shop": "convenience"}},
    {"type": "node", "tags": {"shop": "butcher"}},  # sin coordenadas: se descarta
]}
import time as _t
def post_primero_falla(url, **k):
    if url == u.OVERPASS[0]:
        return R({}, 504)            # el servidor principal falla
    if url == u.OVERPASS[1]:
        _t.sleep(0.3)                # este es lento
    return R(FAKE)
u.requests.post = post_primero_falla
u.requests.get = lambda *a, **k: R([])
u.time.sleep = lambda s: None
t = u.tiendas_cercanas(-2.903, -79.811, 5)  # debe usar uno de respaldo
assert [x["nombre"] for x in t] == ["Tienda de barrio", "Tía Balao", "Mercado Municipal de Balao"], t
assert u.tiendas_para_plan(t) == ["Tienda de barrio", "Tía", "Mercado municipal"]
assert "Tía Balao" in u.resumen_cercanas(t)

def post_siempre_falla(url, **k): raise u.requests.ConnectionError("sin red")
u.requests.post = post_siempre_falla
u.time.sleep = lambda s: None
# Nominatim es la búsqueda principal
NOMI = [{"osm_type": "node", "osm_id": 1, "lat": "-2.17", "lon": "-79.90", "name": "Supermaxi Urdesa", "category": "shop", "type": "supermarket"},
        {"osm_type": "way", "osm_id": 2, "lat": "-2.18", "lon": "-79.89", "name": "Mercado Central", "category": "amenity", "type": "marketplace"},
        {"osm_type": "node", "osm_id": 3, "lat": "-2.17", "lon": "-79.90", "name": "Banco", "category": "amenity", "type": "bank"}]
u.requests.get = lambda *a, **k: R(NOMI)
tb = u.tiendas_cercanas(-2.171, -79.901, 3)
assert sorted(x["nombre"] for x in tb) == ["Mercado Central", "Supermaxi Urdesa"], tb
assert {x["cadena"] for x in tb} == {"Supermaxi", None}
u.requests.get = lambda *a, **k: R([])
try: u.tiendas_cercanas(0, 0); raise SystemExit("debió fallar")
except u.ErrorMapa: pass

u.requests.get = lambda *a, **k: R([])
try: u.geocodificar("Ciudad Inventada"); raise SystemExit("debió fallar")
except u.ErrorMapa as e: assert "No encontré" in str(e)
u.requests.get = lambda *a, **k: R([{"lat": "-2.9", "lon": "-79.8", "display_name": "Balao, Guayas, Ecuador"}])
assert u.geocodificar("Balao")[:2] == (-2.9, -79.8)

assert u.enlace_precio("arroz 5 kg", "Tía").startswith("https://www.tia.com.ec/catalogsearch/result/?q=arroz+5+kg")
assert "Supermaxi" in u.enlace_precio("leche", "Supermaxi").replace("+", " ")
print("PRUEBAS DE UBICACIÓN OK")
assert u.categoria({"cadena": None, "tipo": "Mercado", "nombre": "Mercado Mayorista de Guayaquil"}) == "Mercado mayorista"
assert u.categoria({"cadena": None, "tipo": "Otro", "nombre": "Farmacia"}) is None
assert 12 < u.zoom_para_radio(-2.17, 3) < 15
print("CATEGORÍAS Y ZOOM OK")
