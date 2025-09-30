import gradio as gr
import pandas as pd
from few_shot import clasificar_denuncia, ejemplos
from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay
import matplotlib.pyplot as plt
import os

def clasificar(file): 
    # Leer el archivo
    df = pd.read_json(file.name)
    # Verifica que exista la columna 'denuncias_prueba'
    if 'Hechos' not in df.columns:
        return "El archivo debe tener una columna llamada 'Hechos'.", None

    # Clasificar cada denuncia (procesa una por una)
    clasificaciones = []
    for denuncia in df['Hechos']:
        resultado = clasificar_denuncia(str(denuncia), ejemplos)
        try:
            clasificaciones.append(int(resultado))
        except:
            clasificaciones.append(-1)  # Para errores, marca como -1

    df['clasificacion'] = clasificaciones

    # Guardar el archivo con clasificaciones en la carpeta data
    os.makedirs("data", exist_ok=True)
    output_path2 = os.path.join("data", "denuncias_clasificadas.xlsx")
    df.to_excel(output_path2, index=False)

    output_path = os.path.join("data", "denuncias_clasificadas.json")
    df.to_json(output_path, index=False)

    # Si existe la columna 'etiqueta_real', calcula la matriz de confusión usando el archivo guardado
    cm_fig = None
    if 'DELITO O NO ' in df.columns:
        df_result = pd.read_json(output_path)
        y_true = df_result['DELITO O NO ']
        y_pred = df_result['clasificacion']
        cm = confusion_matrix(y_true, y_pred, labels=[1,0], normalize='true')  # Normaliza a porcentaje
        disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=["Delito (1)", "No delito (0)"])
        fig, ax = plt.subplots(figsize=(6,6))
        disp.plot(ax=ax, values_format=".1%",cmap="jet")
        plt.close(fig)
        cm_fig = fig

    return output_path2, cm_fig

iface = gr.Interface(
    fn=clasificar,
    inputs=gr.File(label="Sube tu archivo"),
    outputs=[
        gr.File(label="Archivo clasificado"),
        gr.Plot(label="Matriz de confusión (si hay etiqueta_real)")
    ],
    title="Clasificador de Denuncias por Lote",
    description=(
        "Sube un archivo con una columna llamada 'Hechos'. "
        "Opcionalmente, agrega una columna 'etiqueta_real' para mostrar la matriz de confusión. "
        "El sistema clasificará cada denuncia como 1 (delito) o 0 (no delito) y te permitirá descargar el archivo clasificado."
    ),
    allow_flagging="never"
)

if __name__ == "__main__":
    iface.launch(inbrowser=True)
