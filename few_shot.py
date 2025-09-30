import pandas as pd
import google.generativeai as genai
import textwrap

# Configura tu API KEY
GOOGLE_API_KEY = "AIzaSyCTzVsUCdcYj6RajYE7TVlAv3IHIXBEg5M"
genai.configure(api_key=GOOGLE_API_KEY)

# Selecciona el modelo
model = genai.GenerativeModel("gemini-2.5-flash")

def to_markdown(text):
    text = text.replace("•", "  *")
    print(textwrap.indent(text, "> ", predicate=lambda _: True))

# Carga datos
df = pd.read_excel("data\REPARTO FISCALIA 111 TRAIN.xlsx")

print(df.columns) 

# Selecciona algunos ejemplos para el prompt (por ejemplo, 3 positivos y 3 negativos)
ejemplos = []
columna1 = 'Hechos'#<-- cambiar nombre
columna2 = 'DELITO O NO '#<-- cambiar nombre
positivos = df[df["DELITO O NO "] == 1]
negativos = df[df["DELITO O NO "] == 0]
for _, row in pd.concat([positivos, negativos]).iterrows():
    ejemplos.append(f'Hechos: "{row[columna1]}"\nRespuesta: {row[columna2]}')

def clasificar_denuncia(Hechos, ejemplos):
    prompt = (
        "Dada los siguiente Hechos, responde solo con 1 si es delito o 0 si no lo es.\n"
        "Ejemplos:\n"
        + "\n\n".join(ejemplos) +
        f"\n\nAhora clasifica esta denuncia:\nDenuncia: \"{Hechos}\"\nRespuesta:"
    )
    response = model.generate_content(prompt)
    return response.text.strip()