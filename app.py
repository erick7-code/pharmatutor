import streamlit as st

import os, google.generativeai as genai
genai.configure(api_key=os.getenv("AIzaSyAS5tRFjc2YVQbPZjl6_4MWlGWpJ7R6ysc"))

def generar_pregunta(topic):
    prompt = f"""
    Genera lo siguiente sobre el tema {topic}:

    1) Un caso clínico breve.
    2) Una pregunta con opciones A, B, C, D.
    3) NO mostrar explicación.
    4) NO mostrar la respuesta correcta.
    5) Al final añade la respuesta correcta dentro de etiquetas <ans></ans>.
       La opción correcta debe ser aleatoria entre A/B/C/D.

    No añadas nada más.
    """

    model = genai.GenerativeModel("models/gemini-2.5-flash")
    response = model.generate_content(prompt).text

    inicio = response.find("<ans>")
    fin = response.find("</ans>")
    correcta = response[inicio+5:fin].strip()
    texto_usuario = response[:inicio].strip()

    return texto_usuario, correcta


def generar_explicacion(topic, correcta):
    prompt = f"""
    Explica si la opción {correcta} es correcta o incorrecta sobre el tema '{topic}'.

    Incluye:
    - Justificación.
    - Por qué las otras opciones no son correctas.
    - Una referencia con link REAL a PubMed/NIH/OMS/CDC.

    Formato:
    1) Explicación.
    2) "Referencia: Título (URL)"
    """

    model = genai.GenerativeModel("models/gemini-2.5-flash")
    return model.generate_content(prompt).text


# ====== APP ======

st.title("Pharmatutor IA 💊")

tema = st.text_input("Ingresa un tema:")
if st.button("Generar pregunta"):
    texto, correcta = generar_pregunta(tema)
    st.session_state.correcta = correcta
    st.session_state.tema = tema
    st.write(texto)

respuesta_usuario = st.text_input("Tu respuesta (A/B/C/D):")
if st.button("Validar respuesta"):
    if respuesta_usuario.upper() == st.session_state.correcta:
        st.success("✅ ¡Correcto!")
    else:
        st.error(f"❌ Incorrecto. La respuesta correcta era: {st.session_state.correcta}")

    st.write("--- Explicación ---")
    explicacion = generar_explicacion(st.session_state.tema, st.session_state.correcta)
    st.write(explicacion)