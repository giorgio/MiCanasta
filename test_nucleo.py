"""Pruebas sin gastar cuota: simulan el cliente de Gemini. Ejecutar: python tests/test_nucleo.py"""
import sys; import os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import nucleo as n

class Resp:
    def __init__(s, obj): s.parsed = obj; s.text = None
class Err(Exception):
    def __init__(s, code): s.code = code
class FakeModels:
    def __init__(s, seq): s.seq = list(seq); s.calls = []
    def generate_content(s, model, contents, config):
        s.calls.append(model); x = s.seq.pop(0)
        if isinstance(x, Exception): raise x
        return Resp(x)
class Fake:
    def __init__(s, seq): s.models = FakeModels(seq)

def item(p, c, pr, t="Tía"):
    return n.ItemCompra(producto=p, categoria="Despensa", cantidad=c, unidad="kg", tienda=t, precio_unitario_usd=pr, motivo="barato")
def plan(items):
    return n.PlanCompras(resumen="ok", items=items, menu_semana_ejemplo=[], consejos=["a"])

# validaciones
assert not n.validar_plan(0, 2, ["Tía"]).ok
assert not n.validar_plan(9000, 2, ["Tía"]).ok
assert not n.validar_plan(100, 2, []).ok
v = n.validar_plan(40, 4, ["Tía"]); assert v.ok and v.avisos
assert not n.validar_recetas("  ").ok
assert n.validar_recetas("arroz").avisos

# plan dentro de presupuesto
c = Fake([plan([item("Arroz", 10, 1.0), item("Huevo", 2, 4.5, "Mercado municipal")])])
r = n.generar_plan(c, 100, 2, 3, "", ["Tía", "Mercado municipal"], "", "", "")
assert r["total"] == 19 and r["dentro_presupuesto"] and not r["corregido"]

# se pasa -> corrige
c = Fake([plan([item("Arroz", 100, 2.0)]), plan([item("Arroz", 30, 2.0)])])
r = n.generar_plan(c, 80, 2, 3, "", ["Tía"], "", "", "")
assert r["corregido"] and r["total"] == 60 and r["dentro_presupuesto"]

# item inválido y tienda no elegida
c = Fake([plan([item("X", 0, 1), item("Pan", 1, 1, "Supermaxi")])])
r = n.generar_plan(c, 50, 1, 3, "", ["Tía"], "", "", "")
assert len(r["plan"].items) == 1 and len(r["avisos"]) == 2

# 429 en principal -> respaldo
c = Fake([Err(429), plan([item("Arroz", 5, 1)])])
r = n.generar_plan(c, 50, 1, 3, "", ["Tía"], "", "", "")
assert r["modelo"] == n.MODELO_RESPALDO

# cuota agotada en ambos
c = Fake([Err(429), Err(429)])
try: n.generar_plan(c, 50, 1, 3, "", ["Tía"], "", "", ""); raise SystemExit("debió fallar")
except n.ErrorIA as e: assert "límite" in str(e)

# clave inválida
c = Fake([Err(403)])
try: n.generar_plan(c, 50, 1, 3, "", ["Tía"], "", "", ""); raise SystemExit("debió fallar")
except n.ErrorIA as e: assert "clave" in str(e)

# recetas
rr = n.RespuestaRecetas(recetas=[], aviso="No son alimentos")
out, _ = n.generar_recetas(Fake([rr]), "piedra, clavo", 2, "")
assert out.aviso

print("TODAS LAS PRUEBAS OK")

# comparador
assert not n.validar_comparacion([], ["Tía", "Supermaxi"]).ok
assert not n.validar_comparacion(["Arroz"], ["Tía"]).ok
P = n.PrecioTienda
comp = n.Comparacion(nota="ok", filas=[
    n.FilaComparacion(producto="Arroz", presentacion="funda 2 kg", precios=[P(tienda="Tía", precio_usd=2.5), P(tienda="Mercado municipal", precio_usd=2.2)]),
    n.FilaComparacion(producto="Atún", presentacion="lata 170 g", precios=[P(tienda="Tía", precio_usd=1.3), P(tienda="Mercado municipal", precio_usd=0)]),
])
filas, tot, gan = n.tabla_comparacion(comp, ["Tía", "Mercado municipal"])
assert filas[0]["Más barato en"] == "Mercado municipal" and filas[0]["Ahorro vs. más caro"] == 0.3
assert filas[1]["Mercado municipal"] is None and filas[1]["Más barato en"] == "Tía"
assert tot == {"Tía": 2.5, "Mercado municipal": 2.2}, tot
assert gan == {"Tía": 1, "Mercado municipal": 1}
r, _ = n.comparar_precios(Fake([comp]), ["Arroz", "Atún"], ["Tía", "Mercado municipal"])
assert len(r.filas) == 2
print("COMPARADOR OK")

# tiendas sin precio quedan fuera
comp2 = n.Comparacion(nota="", filas=[
    n.FilaComparacion(producto="Arroz", presentacion="1 kg", precios=[P(tienda="Tía", precio_usd=1.0), P(tienda="Supermaxi", precio_usd=1.2), P(tienda="Tienda de barrio", precio_usd=0)]),
    n.FilaComparacion(producto="Leche", presentacion="1 l", precios=[P(tienda="Tía", precio_usd=0.9), P(tienda="Supermaxi", precio_usd=0), P(tienda="Tienda de barrio", precio_usd=0)]),
])
assert n.tiendas_con_precio(comp2, ["Tía", "Supermaxi", "Tienda de barrio"]) == ["Tía", "Supermaxi"]
r2 = n.resumen_por_tienda(comp2, ["Tía", "Supermaxi"])
assert r2["Tía"] == {"total": 1.9, "con_precio": 2, "productos": 2} and r2["Supermaxi"]["con_precio"] == 1
assert "Tienda de barrio" not in n.precios_como_texto(comp2, ["Tía", "Supermaxi"])
print("TIENDAS SIN PRECIO OK")
