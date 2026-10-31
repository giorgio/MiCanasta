# AGENTS.md — Canasta Inteligente

Contexto para cualquier agente de programación (Claude, Gemini, Copilot…) que trabaje en este repositorio.

## Qué es
App Streamlit que, a partir de un presupuesto mensual de comida, genera una lista de compras por tienda y recetas nutritivas con ingredientes disponibles. Usuario: hogares de la costa de Ecuador sin perfil técnico. Moneda: USD. Idioma de la interfaz: español neutro (sin voseo).

## Arquitectura
- `app.py`: SOLO interfaz. No pongas lógica de negocio aquí.
- `nucleo.py`: esquemas Pydantic, prompts, `llamar_gemini`, validaciones y cálculos. Debe poder importarse y probarse sin Streamlit.
- `ubicacion.py`: tiendas cercanas con OpenStreetMap (Nominatim y Overpass, con User-Agent propio y caché) y enlaces de precio. No raspar webs de supermercados: Tía lo prohíbe en robots.txt.
- La IA se llama con la librería `google-genai` (`from google import genai`), salida JSON estructurada con `response_schema` = modelo Pydantic.

## Reglas obligatorias
1. **Nunca** escribas la clave de la API en el código. Se lee de `st.secrets["GEMINI_API_KEY"]`.
2. No confíes en los totales que calcule la IA: los totales se calculan en `nucleo.py`.
3. Todo error de la IA se convierte en `ErrorIA` con un mensaje para un usuario no técnico.
4. Valida entradas antes de gastar una consulta.
5. Los precios se presentan siempre como estimados.
6. Los textos visibles son cortos, claros y sin jerga técnica.

## Modelos
- Principal: `gemini-3.8-flash`. Respaldo: `gemini-3.5-flash-lite` (si hay 404 o 429).
- Antes de cambiar de modelo, revisa https://ai.google.dev/gemini-api/docs/deprecations

## Cómo probar
- `streamlit run app.py` con `.streamlit/secrets.toml`.
- Pruebas sin gastar cuota: simular el cliente (`cliente.models.generate_content`) devolviendo objetos con `.parsed`.
- Casos que siempre deben funcionar: presupuesto 0, presupuesto 9000, sin tiendas, ingredientes vacíos, ingredientes que no son comida, plan que se pasa del presupuesto, error 429 en ambos modelos, clave inválida.

## Estilo
Python 3.11+, funciones pequeñas, nombres en español, comentarios solo donde aclaren el porqué.
