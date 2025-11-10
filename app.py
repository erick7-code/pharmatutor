import streamlit as st
import google.generativeai as genai
import re

# ------------------ Config básica ------------------
st.set_page_config(page_title="Pharmatutor IA", page_icon="💊", layout="centered")

# Usa Streamlit Secrets: en .streamlit/secrets.toml define:
# [gemini] api_key = "TU_API_KEY"
API_KEY = st.secrets["gemini"]["api_key"]

# ------------------ Modelo cacheado ------------------
@st.cache_resource(show_spinner=False)
def get_model():
    genai.configure(api_key=API_KEY)
    # Los nombres válidos suelen ser "gemini-1.5-flash" o "gemini-1.5-pro".
    # Si tu cuenta ya tiene 2.5, puedes dejar "models/gemini-2.5-flash".
    return genai.GenerativeModel("gemini-1.5-flash")

model = get_model()

# ------------------ Utilidades ------------------
ANS_RE = re.compile(r"<ans>(.*?)</ans>", re.DOTALL | re.IGNORECASE)
EXP_RE = re.compile(r"<exp>(.*?)</exp>", re.DOTALL | re.IGNORECASE)

def parse_tags(texto: str):
    """Extrae <ans> y <exp> y devuelve (texto_visible, ans, exp)."""
    ans_match = ANS_RE.search(texto)
    exp_match = EXP_RE.search(texto)

    ans = ans_match.group(1).strip() if ans_match else ""
    exp = exp_match.group(1).strip() if exp_match else ""

    # quita las etiquetas del texto a mostrar
    visible = ANS_RE.sub("", texto)
    visible = EXP_RE.sub("", visible)
    visible = visible.strip()
    return visible, ans, exp

# ------------------ Una sola llamada a la API ------------------
def generar_todo(topic: str):
    """
    Hace 1 sola llamada al modelo que devuelve:
    - Caso y pregunta para el usuario
    - Respuesta correcta dentro de <ans> (A/B/C/D)
    - Explicación completa dentro de <exp> (se mostrará tras validar)
    """
    prompt = f"""
Eres un generador de reactivos clínicos. Sobre el tema "{topic}", devuelve EXCLUSIVAMENTE:

1) Un caso clínico breve (2–4 líneas).
2) Una pregunta de opción múltiple con opciones A), B), C), D) en formato limpio.
3) NO muestres explicación ni señales la correcta en el cuerpo visible.
4) Añade la respuesta correcta SOLO dentro de <ans></ans> con una letra A/B/C/D al azar.
5) Añade la explicación completa SOLO dentro de <exp></exp>, incluyendo:
   - Justificación breve de la opción correcta.
   - Por qué las otras opciones no son correctas.
   - 1 referencia con link REAL a PubMed/NIH/OMS/CDC en una sola línea.

Formato esperado (ejemplo):
[Texto visible para el usuario, sin respuestas ni explicación]
<ans>C</ans>
<exp>[Explicación y referencia]</exp>
"""

    # Spinner para feedback inmediato
    with st.spinner("Generando reactivo…"):
        resp = model.generate_content(prompt)
        texto = resp.text

    # Robustez: si por alguna razón no vino texto
    if not texto:
        raise RuntimeError("No se recibió contenido del modelo.")

    # Parseo
    visible, ans, exp = parse_tags(texto)

    # Validaciones mínimas
    if ans.upper() not in {"A", "B", "C", "D"}:
        # fallback: intenta detectar una letra suelta válida
        m = re.search(r"\b([ABCD])\b", texto)
        ans = m.group(1) if m else "A"

    if not exp:
        exp = "Explicación no disponible."

    return visible, ans.upper(), exp

# ------------------ APP ------------------
st.title("Pharmatutor IA")

# Inicializa estado
if "correcta" not in st.session_state:
    st.session_state.correcta = None
if "explicacion" not in st.session_state:
    st.session_state.explicacion = ""
if "texto_visible" not in st.session_state:
    st.session_state.texto_visible = ""
if "tema" not in st.session_state:
    st.session_state.tema = ""

tema = st.text_input("Ingresa un tema (p. ej., 'neumonía adquirida en la comunidad'):")

col1, col2 = st.columns(2)
with col1:
    gen_btn = st.button("Generar pregunta", use_container_width=True)
with col2:
    clear_btn = st.button("Limpiar", type="secondary", use_container_width=True)

if clear_btn:
    st.session_state.correcta = None
    st.session_state.explicacion = ""
    st.session_state.texto_visible = ""
    st.session_state.tema = ""
    st.rerun()

if gen_btn:
    if not tema.strip():
        st.warning("Escribe un tema primero.")
    else:
        try:
            visible, ans, exp = generar_todo(tema.strip())
            st.session_state.tema = tema.strip()
            st.session_state.correcta = ans
            st.session_state.explicacion = exp
            st.session_state.texto_visible = visible
        except Exception as e:
            st.error(f"Ocurrió un error al generar el reactivo: {e}")

if st.session_state.texto_visible:
    st.write(st.session_state.texto_visible)

    respuesta_usuario = st.text_input("Tu respuesta (A/B/C/D):")
    if st.button("Validar respuesta"):
        if not respuesta_usuario:
            st.info("Escribe A, B, C o D.")
        else:
            if respuesta_usuario.strip().upper() == st.session_state.correcta:
                st.success("✅ ¡Correcto!")
            else:
                st.error(f"❌ Incorrecto. La respuesta correcta era: {st.session_state.correcta}")
            st.markdown("---")
            st.subheader("Explicación")
            st.write(st.session_state.explicacion)
