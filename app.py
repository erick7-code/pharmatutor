import os, google.generativeai as genai, streamlit as st

genai.configure(api_key=os.getenv("AIzaSyAS5tRFjc2YVQbPZjl6_4MWlGWpJ7R6ysc"))

@st.cache_resource
def get_model():
    return genai.GenerativeModel(
        "models/gemini-2.5-flash",  # o "models/gemini-2.0-flash-lite-001" si quieres aún más velocidad
        generation_config={"max_output_tokens": 400}  # acota longitud
    )

model = get_model()

def generar_pregunta(topic):
    prompt = f"""
Genera sobre {topic}:
1) Caso clínico breve (≤4 líneas).
2) Una pregunta con opciones A,B,C,D.
3) NO muestres explicación.
4) NO muestres la respuesta correcta.
5) Al final coloca la letra correcta entre <ans> </ans>.
    """.strip()

    # una sola llamada, resultado corto
    txt = model.generate_content(prompt).text
    ini, fin = txt.find("<ans>"), txt.find("</ans>")
    correcta = txt[ini+5:fin].strip() if ini!=-1 and fin!=-1 else None
    visible = txt[:ini].strip() if ini!=-1 else txt.strip()
    return visible, correcta

def generar_explicacion(topic, correcta):
    prompt = f"""
Explica la opción {correcta} para el tema '{topic}':
- Por qué es correcta.
- Por qué las otras no lo son.
- Añade una referencia con link real que respalde lo dicho.
Formato:
1) Explicación.
2) Referencia: Título (URL)
""".strip()
    # streaming para respuesta más rápida de cara al usuario
    stream = model.generate_content(prompt, stream=True)
    stream.resolve()  # junta el stream si prefieres un solo bloque
    return stream.text


# ====== APP ======

st.title("💊 PharmaTutor IA")

with st.form("quiz"):
    tema = st.text_input("Ingresa un tema farmacológico:")
    submitted = st.form_submit_button("Generar pregunta")

if submitted and tema:
    texto, correcta = generar_pregunta(tema)
    st.session_state["pregunta"] = texto
    st.session_state["correcta"]  = correcta
    st.session_state["tema"]      = tema

if "pregunta" in st.session_state:
    st.write("### Caso y pregunta")
    st.write(st.session_state["pregunta"])
    resp = st.text_input("Tu respuesta (A/B/C/D):", key="resp_usuario")
    if st.button("Validar"):
        ok = resp.upper() == st.session_state["correcta"]
        st.success("✅ ¡Correcto!") if ok else st.error(f"❌ Incorrecto. La correcta era: {st.session_state['correcta']}")
        st.write("### Explicación y referencia")
        st.write(generar_explicacion(st.session_state["tema"], st.session_state["correcta"]))