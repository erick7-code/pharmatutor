import os, streamlit as st, google.generativeai as genai
genai.configure(api_key=os.getenv("AIzaSyAS5tRFjc2YVQbPZjl6_4MWlGWpJ7R6ysc"))

@st.cache_resource
def get_model():
    return genai.GenerativeModel(
        "models/gemini-2.5-flash",
        generation_config={"max_output_tokens": 400, "temperature": 0.6}
    )

model = get_model()

def _extract_text(resp):
    # Ensambla texto sin usar resp.text (evita el ValueError)
    if not getattr(resp, "candidates", None):
        return ""
    out = []
    for c in resp.candidates:
        if getattr(c, "content", None) and getattr(c.content, "parts", None):
            for p in c.content.parts:
                if getattr(p, "text", None):
                    out.append(p.text)
    return "\n".join(out).strip()

def generar_pregunta(topic):
    prompt = f"""
Genera sobre {topic}:
1) Caso clínico breve (≤4 líneas).
2) Pregunta con opciones A,B,C,D.
3) NO muestres explicación.
4) NO muestres la respuesta correcta.
5) Al final coloca SOLO la letra correcta entre <ans></ans>.
""".strip()

    resp = model.generate_content(prompt)
    txt  = _extract_text(resp)

    ini, fin = txt.find("<ans>"), txt.find("</ans>")
    if ini == -1 or fin == -1:
        raise RuntimeError("No llegó <ans> del modelo.")
    correcta = txt[ini+5:fin].strip()
    visible  = txt[:ini].strip()
    return visible, correcta

def generar_explicacion(topic, correcta):
    prompt = f"""
Explica por qué la opción {correcta} es correcta para '{topic}' y por qué las otras no.
Al final agrega una referencia con link real (PubMed/NIH/OMS/CDC).
Formato:
1) Explicación.
2) Referencia: Título (URL)
""".strip()
    resp = model.generate_content(prompt)
    return _extract_text(resp)
