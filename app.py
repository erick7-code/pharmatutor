import os
import google.generativeai as genai
import streamlit as st
from google.generativeai.types import HarmCategory, HarmBlockThreshold

genai.configure(api_key=os.getenv("AIzaSyAS5tRFjc2YVQbPZjl6_4MWlGWpJ7R6ysc"))

# ---------- Config y utilidades ----------
SAFETY = {
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUAL: HarmBlockThreshold.BLOCK_NONE,
}

@st.cache_resource
def get_model(primary=True):
    model_id = "models/gemini-2.5-flash" if primary else "models/gemini-2.0-flash-lite-001"
    return genai.GenerativeModel(
        model_id,
        generation_config={
            "max_output_tokens": 400,
            "temperature": 0.6,
        },
        safety_settings=SAFETY
    )

def _extract_text(resp):
    """
    Ensambla texto sin usar response.text (que falla si no hay Part).
    """
    if not getattr(resp, "candidates", None):
        return ""
    out = []
    for c in resp.candidates:
        if hasattr(c, "content") and getattr(c.content, "parts", None):
            for p in c.content.parts:
                if hasattr(p, "text") and p.text:
                    out.append(p.text)
    return "\n".join(out).strip()

def _gen_with_fallback(prompt):
    """
    Intenta con 2.5-flash; si bloquea o viene vacío, reintenta con 2.0-flash-lite-001.
    """
    # 1) Intento principal
    m = get_model(primary=True)
    resp = m.generate_content(prompt)
    txt = _extract_text(resp)
    if txt:
        return txt

    # 2) Reintento con modelo lite
    m2 = get_model(primary=False)
    resp2 = m2.generate_content(prompt)
    txt2 = _extract_text(resp2)
    if txt2:
        return txt2

    # 3) Mensaje claro de error si sigue vacío
    # (Incluye motivo si existe)
    fr = None
    pf = None
    try:
        fr = resp.candidates[0].finish_reason if resp and resp.candidates else None
        pf = getattr(resp, "prompt_feedback", None)
    except Exception:
        pass
    raise RuntimeError(f"El modelo no devolvió contenido. finish_reason={fr} prompt_feedback={pf}")

# ---------- Tu lógica ----------
def generar_pregunta(topic):
    prompt = f"""
Genera sobre {topic}:
1) Caso clínico breve (≤4 líneas).
2) Una pregunta con opciones A, B, C, D.
3) NO muestres explicación.
4) NO muestres la respuesta correcta.
5) Al final coloca SOLO la letra correcta entre <ans></ans>.
   La letra correcta debe corresponder a las opciones mostradas y variar entre A/B/C/D.

Formato estricto, sin texto extra fuera del esquema.
""".strip()

    txt = _gen_with_fallback(prompt)

    # Extraer <ans> con tolerancia
    ini, fin = txt.find("<ans>"), txt.find("</ans>")
    correcta = None
    visible = txt
    if ini != -1 and fin != -1 and fin > ini + 5:
        correcta = txt[ini+5:fin].strip()
        visible = txt[:ini].strip()

    # Reparación si no llegó <ans>
    if not correcta or correcta not in {"A", "B", "C", "D"}:
        fix_prompt = f"""
Repara el siguiente contenido para que cumpla el formato solicitado y añade <ans> con A/B/C/D al final.
No expliques nada adicional.

Contenido a reparar:
{txt}
""".strip()
        txt2 = _gen_with_fallback(fix_prompt)
        ini2, fin2 = txt2.find("<ans>"), txt2.find("</ans>")
        if ini2 != -1 and fin2 != -1 and fin2 > ini2 + 5:
            correcta = txt2[ini2+5:fin2].strip()
            visible = txt2[:ini2].strip()
        else:
            # Último recurso: abortar con mensaje claro
            raise RuntimeError("No se pudo obtener la respuesta correcta (<ans>) del modelo.")

    return visible, correcta

def generar_explicacion(topic, correcta):
    prompt = f"""
Explica la opción {correcta} para el tema '{topic}':
- Por qué es correcta.
- Por qué las otras no lo son.
- Al final agrega una referencia con link REAL y confiable (PubMed/NIH/OMS/CDC) que respalde lo explicado.
Formato:
1) Explicación.
2) Referencia: Título (URL)
""".strip()
    txt = _gen_with_fallback(prompt)
    return txt
