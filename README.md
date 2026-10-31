# 🛒 Canastas

Aplicación web que ayuda a una familia a **estirar su presupuesto mensual de comida**: le dices cuánto tienes, cuántas personas comen y en qué tiendas puedes comprar, y te devuelve **qué comprar, en qué tienda y cuánto gastarás**. Además, en una segunda pestaña te propone **recetas nutritivas con lo que ya tienes en la cocina**.

- **App desplegada:** https://canastas.streamlit.app
- **Autor:** Jorge Recabarren
- **IA usada:** Google Gemini (`gemini-3.8-flash`, con `gemini-3.5-flash-lite` como respaldo)

## Problema y usuario

Hogares de la costa ecuatoriana (por ejemplo, en Guayaquil) con un presupuesto fijo y ajustado para la comida. Hoy organizan la compra "de memoria": van al mercado o al supermercado sin lista, compran por impulso y a fin de mes falta dinero o falta comida. Cuando hay pocos ingredientes en casa, terminan cocinando siempre lo mismo.

**Qué resuelve la IA:** estimar cantidades y precios para todo un mes, repartir la compra entre tiendas y crear recetas con ingredientes concretos.
**Qué queda fuera:** precios exactos en tiempo real (son estimaciones), consejo médico o dietas clínicas.

## Funcionalidades

- **📍 Tiendas cerca de ti:** con el GPS del celular o la ciudad, muestra en un mapa fijo (sin mover ni zoom) las tiendas reales cercanas en verde y tu ubicación en rojo (OpenStreetMap), con distancia y enlace para llegar.
- **📊 Comparación automática:** al encontrar las tiendas cercanas, la app compara tus productos en cada tipo de tienda (mercado, Tía, Mi Comisariato, Akí, Supermaxi, Coral, TuTi…) y deja fuera las que no tienen precios. Ves el precio estimado de cada uno en cada tienda, cuál es la más barata, el ahorro y el total por tienda.
- **🥗 Una receta saludable cada semana:** con los productos de la lista crea 4 recetas (una por semana) y las entrega como archivo de calendario (.ics): al abrirlo en el celular, cada semana llega un aviso con la receta.

| Pestaña | Entrada | Salida |
|---|---|---|
| 🧾 Mi compra del mes | Presupuesto (USD), personas, comidas al día, tiendas, restricciones, lo que ya hay en casa, precios conocidos | Lista por tienda con cantidades, precio y subtotal; total y sobrante; menú semanal de ejemplo; consejos; descarga para imprimir |
| 📊 Comparar precios | Productos, tiendas, ciudad, precios vistos | Tabla producto × tienda, tienda más barata, ahorro, total por tienda, enlaces y CSV |
| 🍳 ¿Qué cocino hoy? | Ingredientes disponibles, personas, restricciones | 3 recetas con pasos, lo que falta comprar y su costo, calorías y proteína aproximadas |

## Cómo usarla

1. **Paso 1:** escribe tu presupuesto mensual, cuántas personas comen y tu ciudad o barrio (por defecto, Guayaquil).
2. **Paso 2:** elige qué productos comparar y, si quieres, pulsa **Usar mi ubicación (GPS)**. Verás un mapa fijo con las tiendas cercanas en verde y tu ubicación en rojo, la tabla de precios de tus productos en cada tienda y la lista de tiendas cercanas ordenada de la más barata a la más cara. Las tiendas sin precios no aparecen.
3. **Paso 3:** pulsa **Armar mi lista del mes** y la app arma la compra del mes con esas tiendas y esos precios. Puedes descargarla para imprimir. Abajo, **Crear mis 4 recetas semanales** y **Añadir a mi calendario** para recibir una receta saludable cada semana.
4. En el menú lateral, **¿Qué cocino hoy?** te da recetas con lo que tienes en casa.

## Ejecutar en local

```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # y pega tu clave
streamlit run app.py
```

La clave se obtiene gratis en [Google AI Studio](https://aistudio.google.com/apikey).

## Desplegar en Streamlit Community Cloud

1. Sube este repositorio a GitHub (público). `secrets.toml` está en `.gitignore` y **nunca** se sube.
2. En [share.streamlit.io](https://share.streamlit.io) → **Create app** → elige el repo y `app.py`.
3. En **Advanced settings → Secrets** pega: `GEMINI_API_KEY = "tu-clave"`.

## Estructura

```
app.py           Interfaz (Streamlit)
ubicacion.py     Tiendas cercanas (OpenStreetMap: Nominatim + Overpass) y enlaces de precio
tests/           Pruebas sin internet ni cuota
nucleo.py        Lógica: esquemas, prompts, llamada a Gemini, validaciones y cálculos
PROMPTS.md       Prompts reutilizables de la app
AGENTS.md        Contexto para el agente de programación
requirements.txt Dependencias
```

## Cómo maneja errores y límites

- Valida las entradas **antes** de llamar a la IA (presupuesto 0 o absurdo, sin tiendas, sin ingredientes).
- La app **recalcula el total ella misma**; si la IA se pasa del presupuesto, le pide una corrección automática una vez.
- Si el modelo principal no tiene cuota (error 429) o no existe (404), usa el modelo de respaldo.
- Mensajes claros para clave inválida, cuota agotada o servicio saturado; espera de 8 s entre consultas para cuidar la cuota gratuita.

## Limitaciones

**Por qué los precios no se leen automáticamente de los supermercados:** Tía bloquea su API de catálogo y su robots.txt prohíbe el acceso automático a su buscador; leer precios en vivo con la búsqueda de Google desde Gemini solo está disponible con facturación activada. Por eso la app muestra precios estimados con IA y lo indica en pantalla.


Los precios son estimaciones de la IA y pueden diferir de los reales; la app lo indica en pantalla. La información nutricional es aproximada y no reemplaza a un profesional de salud.
