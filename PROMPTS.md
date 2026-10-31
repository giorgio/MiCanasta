# Prompts de Canastas

Los prompts viven en `nucleo.py` como plantillas reutilizables (`str.format`). Aquí se documentan y se explica por qué están escritos así.

## 1. Instrucción de sistema (`SISTEMA`)
Define el rol: asistente de economía doméstica y nutrición para hogares de Ecuador, en USD, que da precios como **estimaciones**, prioriza comida típica y barata (arroz, menestras, verde, yuca, huevos, pollo, pescado, atún, frutas de temporada), no da consejo médico y responde en español neutro.

**Por qué:** fija el contexto local (moneda y productos) y evita que la IA presente precios como exactos o dé consejos de salud.

## 2. Plan mensual (`PROMPT_PLAN`)
Variables: `presupuesto`, `personas`, `comidas`, `ciudad`, `tiendas`, `restricciones`, `en_casa`, `precios_conocidos`, `correccion`.

Reglas que impone:
1. Suma de cantidad × precio ≤ presupuesto, con 3–8 % de margen.
2. Cantidades para 30 días y N personas.
3. Cada producto en la tienda más barata para su tipo (mercado/feria para frescos, supermercado para empacados).
4. El precio es por UNA unidad (evita confundir precio total con unitario).
5. Cubrir energía, proteína, frutas y verduras.
6. Entre 12 y 30 productos; sin chatarra ni bebidas azucaradas.

**Salida:** JSON validado con el esquema `PlanCompras` (resumen, items, menú de 7 días, consejos).

**Bucle de corrección:** si el total calculado por la app supera el presupuesto, se reenvía el mismo prompt con `correccion` = "tu propuesta costaba X y el presupuesto es Y; reduce...". Se conserva la versión más barata.

## 3. Recetas (`PROMPT_RECETAS`)
Variables: `ingredientes`, `personas`, `restricciones`.

Reglas: usar sobre todo lo disponible (se asume sal, agua y aceite); faltantes baratos (< 2 USD) y con costo; pasos cortos para alguien que cocina poco; calorías y proteína aproximadas; si los ingredientes no alcanzan o no son comida, devolver lista vacía y explicar en `aviso`.

**Salida:** JSON con el esquema `RespuestaRecetas`.

## 4. Comparar precios (`PROMPT_COMPARAR`)
Variables: `productos`, `tiendas`, `ciudad`, `precios_conocidos`. Pide la misma presentación para todas las tiendas (para que sean comparables), todas las tiendas en cada fila, 0 si no lo venden, y respeta los precios que el usuario vio. La app decide cuál es la más barata y calcula ahorros y totales.

## Prompts usados con el agente de programación
1. *"Lee AGENTS.md. Construye una app Streamlit con dos pestañas: plan de compras mensual por tienda y recetas con lo que hay en casa. Separa interfaz (app.py) y lógica (nucleo.py). Usa google-genai con salida JSON estructurada mediante Pydantic."*
2. *"La IA a veces suma mal. Haz que la app calcule los totales y, si se pasa del presupuesto, pida una corrección una sola vez."*
3. *"Añade manejo de errores: 401/403 clave inválida, 429 cuota, 404 modelo inexistente, 5xx saturado. Si el modelo principal falla por cuota, usa uno de respaldo. Mensajes para usuario no técnico."*
4. *"Escribe pruebas que simulen el cliente de Gemini para no gastar cuota: plan dentro de presupuesto, plan que se pasa, item con precio 0, tienda no elegida, 429 en ambos modelos, clave inválida, ingredientes que no son comida."*
5. *"Agrega botones 'Cargar ejemplo' para que un usuario nuevo vea la app funcionando sin escribir nada."*
6. *"La lista tardaba unos 100 segundos: baja el razonamiento del modelo a nivel bajo, limita a 22 productos y frases cortas."*
7. *"Agrega una pestaña para comparar precios de varios productos entre varias tiendas y marca la más barata."*
