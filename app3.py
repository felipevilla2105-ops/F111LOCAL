import gradio as gr
import pandas as pd
import os
import matplotlib.pyplot as plt  # Se mantiene la importación por convención, aunque ya no se use para la matriz
from few_shot import clasificar_denuncia, ejemplos # Asume que estas importaciones son necesarias para la clasificación

# --- Lógica de la Aplicación ---
def clasificar(file):
    """
    Lee un archivo JSON/CSV, clasifica el texto en la columna 'Hechos'
    y guarda el resultado en un archivo Excel.
    """
    
    # 1. Cargar el archivo
    # Se asume que el archivo subido es un archivo de pandas compatible (e.g., JSON, CSV)
    # y que file.name contiene la ruta temporal.
    try:
        # Intentar leer como JSON primero, ya que el original lo hacía
        df = pd.read_json(file.name)
    except ValueError:
        # Si falla, intentar leer como CSV (es una suposición común en Gradio File)
        try:
            df = pd.read_csv(file.name)
        except Exception as e:
            # Manejar cualquier otro error de lectura
            return f"Error al leer el archivo: {e}. Asegúrate de que sea un JSON o CSV válido.", None
        
    # 2. Validación de columna
    HECHOS_COL = 'Hechos'
    if HECHOS_COL not in df.columns:
        return f"El archivo debe tener una columna llamada '{HECHOS_COL}'.", None

    # 3. Clasificar las denuncias (procesa una por una)
    clasificaciones = []
    for denuncia in df[HECHOS_COL]:
        # Asegura que la entrada a clasificar_denuncia sea una cadena
        resultado = clasificar_denuncia(str(denuncia), ejemplos)
        try:
            # Intenta convertir el resultado a entero (1 o 0)
            clasificaciones.append(int(resultado))
        except:
            # Para errores en la clasificación (e.g., no devuelve 1 o 0), marca como -1
            clasificaciones.append(-1)
            
    df['clasificacion'] = clasificaciones

    # 4. Guardar el archivo clasificado
    
    # Crea la carpeta 'data' si no existe
    os.makedirs("data", exist_ok=True)
    
    # Define la ruta de salida (usaremos solo Excel por simplicidad y usabilidad)
    output_path = os.path.join("data", "denuncias_clasificadas.xlsx")
    
    # Guardar en Excel
    df.to_excel(output_path, index=False)

    # Devolver la ruta del archivo guardado
    return output_path

# --- Interfaz de Gradio ---
# Se elimina el output gr.Plot()
iface = gr.Interface(
    fn=clasificar,
    inputs=gr.File(label="Sube tu archivo (JSON o CSV)"),
    outputs=gr.File(label="Archivo clasificado (Excel)"),
    title="Clasificador de Denuncias por Lote",
    description=(
        "Sube un archivo (JSON o CSV) con una columna llamada 'Hechos'. "
        "El sistema clasificará cada denuncia como 1 (delito), 0 (no delito) o -1 (error de clasificación), "
        "agregará la columna 'clasificacion', y te permitirá descargar el archivo resultante en formato Excel."
    ),
    allow_flagging="never"
)

# --- Lanzamiento ---
if __name__ == "__main__":
    iface.launch(inbrowser=True)