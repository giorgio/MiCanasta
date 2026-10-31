# 🛒 Canasta Inteligente

Aplicación web que ayuda a una familia a **estirar su presupuesto mensual de comida**: le dices cuánto tienes, cuántas personas comen y en qué tiendas puedes comprar, y te devuelve **qué comprar, en qué tienda y cuánto gastarás**. Además, en una segunda pestaña te propone **recetas nutritivas con lo que ya tienes en la cocina**.

- **App desplegada:** _pega aquí el enlace de Streamlit Community Cloud_
- **Autor:** Jorge Recabarren
- **IA usada:** Google Gemini (`gemini-3.8-flash`, con `gemini-3.5-flash-lite` como respaldo)

## Problema y usuario

Hogares de la costa ecuatoriana (por ejemplo, en Balao) con un presupuesto fijo y ajustado para la comida. Hoy organizan la compra "de memoria": van al mercado o al supermercado sin lista, compran por impulso y a fin de mes falta dinero o falta comida. Cuando hay pocos ingredientes en casa, terminan cocinando siempre lo mismo.

**Qué resuelve la IA:** estimar cantidades y precios para todo un mes, repartir la compra entre tiendas y crear recetas con ingredientes concretos.
**Qué queda fuera:** precios exactos en tiempo real (son estimaciones), consejo médico o dietas clínicas.

## Funcionalidades

- **📍 Tiendas cerca de ti:** con el GPS del celular o escribiendo la ciudad, muestra en un mapa los supermercados, mercados y tiendas reales cercanos (OpenStreetMap), con distancia y enlace para llegar. Un botón marca esas cadenas en el formulario.
- **Ver precio hoy:** cada producto de la lista tiene un enlace que abre la búsqueda de ese producto en la web de la tienda (Tía) o en Google, para confirmar el precio actual.

| Pestaña | Entrada | Salida |
|---|---|---|
| 🧾 Mi compra del mes | Presupuesto (USD), personas, comidas al día, tiendas, restricciones, lo que ya hay en casa, precios conocidos | Lista por tienda con cantidades, precio y subtotal; total, sobrante y gráfico por tienda; menú semanal de ejemplo; consejos; descarga CSV y TXT |
| 🍳 ¿Qué cocino hoy? | Ingredientes disponibles, personas, restricciones | 3 recetas con pasos, lo que falta comprar y su costo, calorías y proteína aproximadas |

## Cómo usarla

1. Abre la app y pulsa **Cargar ejemplo** para ver un caso completo.
2. Cambia el presupuesto, las personas y marca tus tiendas.
3. Pulsa **Armar mi lista** y descarga la lista para llevarla al mercado.
4. En **¿Qué cocino hoy?**, escribe lo que tienes y pulsa **Dame recetas**.

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

**Por qué los precios no se leen automáticamente de los supermercados:** Tía bloquea su API de catálogo y su robots.txt prohíbe el acceso automático a su buscador; leer precios en vivo con la búsqueda de Google desde Gemini solo está disponible con facturación activada. Por eso la app estima los precios con IA, deja que el usuario escriba los que vio y ofrece un enlace directo al precio de hoy.


Los precios son estimaciones de la IA y pueden diferir de los reales; la app lo indica en pantalla. La información nutricional es aproximada y no reemplaza a un profesional de salud.
