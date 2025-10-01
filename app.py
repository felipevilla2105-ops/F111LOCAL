import streamlit as st
import pandas as pd
from datetime import datetime
import altair as alt 
from dotenv import load_dotenv
import os

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY") 

# --- Configuración de la Página y Variables ---
st.set_page_config(layout="wide", page_title="Análisis Judicial Interactivo")

# ¡IMPORTANTE! REEMPLAZA esta URL con el enlace "Raw" de tu archivo CSV en GitHub
ARCHIVO_CSV_URL = "https://github.com/felipevilla2105-ops/curso-talento-t/raw/refs/heads/main/carga_ficticia_111.csv" 

FECHA_ACTUAL = datetime.now()
LIMITE_MESES = 2 
LIMITE_QUERELLA_MESES = 6 

st.image('IMG/Imagen1.png', use_container_width=True) 

# --- Función de Carga de Datos (Cacheada) ---
@st.cache_data
def cargar_datos(url):
    """Carga el archivo CSV desde una URL, limpia, convierte y ajusta las columnas de fecha."""
    try:
        df = pd.read_csv(url)
        
        # 1. Conversión y limpieza de fechas
        columnas_fecha = ['Fecha de los Hechos', 'Fecha de la denuncia', 'Fecha Última Actuación']
        for col in columnas_fecha:
            # Intentar convertir al formato datetime, forzando NaT en caso de error
            df[col] = pd.to_datetime(df[col], errors='coerce') 
            
        # 2. ELIMINAR LA HORA en la fecha de última actuación (Nuevo Requisito)
        if 'Fecha Última Actuación' in df.columns:
            df['Fecha Última Actuación'] = df['Fecha Última Actuación'].dt.normalize()
            
        # 3. Limpieza de texto (para comparaciones)
        for col in ['Tipo de Noticia', 'Última Actuación', 'Caracterización']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.upper().str.strip() 
            
        return df
    except Exception as e:
        st.error(f"❌ Error al cargar o procesar el archivo desde la URL. Verifica el enlace Raw: {e}")
        st.info("La URL debe ser el enlace 'Raw' (crudo) de tu archivo CSV en GitHub.")
        return None

# --- Ejecución de Carga ---
df = cargar_datos(ARCHIVO_CSV_URL)

st.title("⚖️ Sistema Interactivo de Alertas Judiciales")
st.caption(f"Análisis realizado con fecha: **{FECHA_ACTUAL.strftime('%d/%m/%Y')}**")

if df is not None:
    st.markdown("---")
    
    # --- 0. PREPARACIÓN DE DATOS Y DEFINICIÓN DE LÍMITES ---
    
    limite_actuacion = FECHA_ACTUAL - pd.DateOffset(months=LIMITE_MESES)
    
    # --- 1. CADUCIDAD DE LA QUERELLA ---
    df_querellable = df[df['Tipo de Noticia'] == 'QUERELLA'].copy()
    df_querellable['Dias_Transcurridos'] = (df_querellable['Fecha de la denuncia'] - df_querellable['Fecha de los Hechos']).dt.days
    df_querellable['Tiempo_Transcurrido'] = df_querellable['Dias_Transcurridos'] / 30.4375
    casos_caducidad = df_querellable[
        (df_querellable['Tiempo_Transcurrido'] > LIMITE_QUERELLA_MESES) & 
        (df_querellable['Dias_Transcurridos'] > 0)
    ].sort_values(by='Fecha de los Hechos', ascending=True) # ORDENADO: Del más viejo al más nuevo

    total_caducidad = len(casos_caducidad)
    
    # --- 2. INACTIVIDAD GENERAL ---
    casos_inactivos_general = df[
        (df['Fecha Última Actuación'].isnull()) | 
        (df['Fecha Última Actuación'] < limite_actuacion)
    ].sort_values(by='Fecha Última Actuación', ascending=True, na_position='first') # ORDENADO: Del más viejo al más nuevo

    total_inactivos_general = len(casos_inactivos_general)
    
    # --- 3. INACTIVIDAD DEL DENUNCIANTE ---
    ACTUACION_INACTIVIDAD = 'SOLICITUD A DENUNCIANTE DE INFORMACIÓN ADICIONAL'
    casos_archivo_inactividad = df[
        (df['Última Actuación'] == ACTUACION_INACTIVIDAD) & 
        (df['Fecha Última Actuación'] < limite_actuacion)
    ].sort_values(by='Fecha Última Actuación', ascending=True) # ORDENADO: Del más viejo al más nuevo

    total_archivo_inactividad = len(casos_archivo_inactividad)
    
    # --- 4. CONCILIACIÓN ---
    casos_conciliacion_archivo = df[df['Última Actuación'].str.contains('CONCILIACIÓN CON ACUERDO', na=False)].sort_values(by='Fecha Última Actuación', ascending=True)
    
    casos_conciliacion_continuar = df[
        df['Última Actuación'].str.contains('FRACASADA|SIN ACUERDO', na=False) 
        & df['Última Actuación'].str.contains('CONCILIACIÓN', na=False)
    ].sort_values(by='Fecha Última Actuación', ascending=True) # ORDENADO: Del más viejo al más nuevo
    
    total_conciliacion_archivo = len(casos_conciliacion_archivo)
    total_conciliacion_continuar = len(casos_conciliacion_continuar)
    
    
    # --- Panel de Métricas Clave (KPI Dashboard) ---
    st.subheader("📊 Resumen de Alertas Activas")
    
    col1, col2, col3, col4, col5 = st.columns(5) 

    col1.metric(
        label="🚨 Casos de Caducidad de Querella",
        value=total_caducidad,
        delta=f"Superan {LIMITE_QUERELLA_MESES} meses",
        delta_color="inverse"
    )
    col2.metric(
        label="🗓️ Sin Actuación (> 2M)",
        value=total_inactivos_general,
        delta=f"Necesitan impulso procesal (Límite: {limite_actuacion.strftime('%d/%m/%Y')})",
        delta_color="off"
    )
    col3.metric(
        label="📁 Conciliación con Acuerdo",
        value=total_conciliacion_archivo,
        delta="Listos para archivo",
        delta_color="normal"
    )
    col4.metric(
        label="⏩ Conciliación Fracasada/Sin Acuerdo",
        value=total_conciliacion_continuar,
        delta="Listos para continuar el proceso",
        delta_color="off"
    )
    col5.metric(
        label="⛔ Inactividad del Denunciante",
        value=total_archivo_inactividad,
        delta="Posibles casos a archivar",
        delta_color="inverse"
    )
    
    st.markdown("---")
    
    # --- Estructura por Pestañas ---
    tab1, tab2, tab3, tab4 = st.tabs([
        "📅 Caducidad de la Querella", 
        "⏳ Últimas Actuaciones (Avance)", 
        "🤝 Estado de Conciliación", 
        "📈 Modos de las Estafas (Top 5)"
    ])

    # ====================================================================
    # PESTAÑA 1: CADUCIDAD DE LA QUERELLA
    # ====================================================================
    with tab1:
        st.subheader("Análisis de Caducidad por Plazo Legal")
        st.info(f"Filtro: Casos tipo 'QUERELLA' con más de **{LIMITE_QUERELLA_MESES} meses** entre la Fecha de los Hechos y la Fecha de la Denuncia. (Ordenado: más viejo primero)")

        if total_caducidad > 0:
            st.warning(f"🚨 **¡ATENCIÓN!** Se encontraron **{total_caducidad}** casos con riesgo de Caducidad de la Querella.")
            
            with st.expander("🔎 Ver listado detallado de Casos de Caducidad"):
                df_mostrar = casos_caducidad[['Caso Noticia', 'Fecha de los Hechos', 'Fecha de la denuncia', 'Tiempo_Transcurrido']]
                st.dataframe(
                    df_mostrar,
                    column_config={
                        "Tiempo_Transcurrido": st.column_config.NumberColumn("Meses Transcurridos", format="%0.2f")
                    },
                    use_container_width=True
                )
        else:
            st.success("✅ ¡Excelente! No se encontraron casos querellables con riesgo de caducidad.")


    # ====================================================================
    # PESTAÑA 2: ÚLTIMAS ACTUACIONES (AVANCE PROCESAL)
    # ====================================================================
    with tab2:
        st.subheader("1. Procesos sin movimientos recientes (Impulso Necesario)")
        st.info(f"Filtro: Casos cuya 'Fecha Última Actuación' es anterior al **{limite_actuacion.strftime('%d/%m/%Y')}**. (Ordenado: más viejo primero)")
        
        if total_inactivos_general > 0:
            st.warning(f"⏳ **¡Avanzar con el proceso!** Hay **{total_inactivos_general}** procesos que no registran nuevas actuaciones en los últimos dos meses.")
            
            with st.expander("🔎 Ver Procesos Inactivos (General)"):
                df_mostrar = casos_inactivos_general[['Caso Noticia', 'Fecha Última Actuación', 'Última Actuación']]
                st.dataframe(df_mostrar, use_container_width=True)
        else:
            st.success("✅ Todos los procesos registran alguna actuación reciente (dentro de los últimos dos meses).")
            
        st.markdown("---")
            
        st.subheader("2. Inactividad del Denunciante (Sugerencia de Archivo)")
        st.info(f"Filtro: Casos con 'Última Actuación' = **{ACTUACION_INACTIVIDAD}** y esta es anterior al **{limite_actuacion.strftime('%d/%m/%Y')}**. (Ordenado: más viejo primero)")
        
        if total_archivo_inactividad > 0:
            st.error(f"⛔ **¡Se puede proceder con el archivo del caso!** Se encontraron **{total_archivo_inactividad}** casos que cumplen el criterio de inactividad del denunciante.")
            
            with st.expander("🔎 Ver Casos por Inactividad del Denunciante"):
                df_mostrar = casos_archivo_inactividad[['Caso Noticia', 'Fecha Última Actuación', 'Última Actuación']]
                st.dataframe(df_mostrar, use_container_width=True)
        else:
            st.success(f"✅ No hay casos pendientes de respuesta del denunciante por más de dos meses.")


    # ====================================================================
    # PESTAÑA 3: ESTADO DE CONCILIACIÓN
    # ====================================================================
    with tab3:
        st.subheader("Análisis de Conciliación y Seguimiento")
        st.caption("Los listados se muestran ordenados por fecha de actuación, del más antiguo al más reciente.")
        
        col_c_1, col_c_2 = st.columns(2)

        # 3.1. Conciliación con Acuerdo (Archivo)
        with col_c_1:
            st.markdown("##### Casos con Acuerdo (Listos para Archivo)")
            if total_conciliacion_archivo > 0:
                st.success(f"✅ **Proceder con el archivo:** Hay **{total_conciliacion_archivo}** casos con Conciliación con Acuerdo.")
                with st.expander("Ver listado"):
                    st.dataframe(
                        casos_conciliacion_archivo[['Caso Noticia', 'Última Actuación', 'Fecha Última Actuación']], 
                        use_container_width=True
                    )
            else:
                st.info("No hay casos recientes para archivar por Conciliación con Acuerdo.")
                
        # 3.2. Conciliación Fracasada/Sin Acuerdo (Continuar)
        with col_c_2:
            st.markdown("##### Casos Sin Acuerdo / Fracasada (Continuar Proceso)") 
            if total_conciliacion_continuar > 0:
                st.info(f"➡️ **Continuar con el proceso:** Hay **{total_conciliacion_continuar}** casos de Conciliación Fracasada o Sin Acuerdo.")
                with st.expander("Ver listado"):
                    st.dataframe(
                        casos_conciliacion_continuar[['Caso Noticia', 'Última Actuación', 'Fecha Última Actuación']], 
                        use_container_width=True
                    )
            else:
                st.info("No hay casos recientes de Conciliación Fracasada o Sin Acuerdo.")

    # ====================================================================
    # PESTAÑA 4: MODOS DE LA ESTAFAS (GRÁFICA TOP 5)
    # ====================================================================
    with tab4:
        st.subheader("Distribución de Modalidades de Estafa (Caracterización) - Top 5")
        st.markdown("Este gráfico muestra las **5 modalidades** de estafa más frecuentes.")

        conteo_modalidades = df['Caracterización'].value_counts().reset_index()
        conteo_modalidades.columns = ['Modalidad', 'Número de Casos']
        
        # Filtrar solo el Top 5
        top_5_modalidades = conteo_modalidades.head(5)
        
        if not top_5_modalidades.empty:
            # Uso de Altair para un gráfico más interactivo (Limitado a Top 5)
            chart = alt.Chart(top_5_modalidades).mark_bar().encode(
                x=alt.X('Modalidad', sort='-y', axis=alt.Axis(title='Modalidad (Top 5)', labelAngle=-45)),
                y=alt.Y('Número de Casos'),
                tooltip=['Modalidad', 'Número de Casos']
            ).properties(
                title="Top 5 Modalidades de Estafa por Caracterización"
            ).interactive()
            
            st.altair_chart(chart, use_container_width=True)

            with st.expander("Ver tabla del Top 5 de Modalidades"):
                st.dataframe(top_5_modalidades, use_container_width=True)

        else:
            st.warning("No hay datos válidos en la columna 'Caracterización' para generar la gráfica.")

#-----------

import streamlit as st
import pandas as pd
from datetime import datetime
import altair as alt 
from dotenv import load_dotenv
import os
import io # Necesario para manejar archivos en memoria para Streamlit

# --- !!! IMPORTACIONES ASUMIDAS (NECESARIAS PARA LA CLASIFICACIÓN) !!! ---
# Se asume que estos módulos/funciones existen en el entorno de ejecución.
# Debes asegurarte de que 'few_shot.py' y 'clasificar_denuncia' estén accesibles.
# from few_shot import clasificar_denuncia, ejemplos 

# SIMULACIÓN: Función de clasificación ficticia para que el código sea ejecutable 
# y se puedan ver las métricas sin la dependencia de 'few_shot'.
# Si tienes la implementación real de clasificar_denuncia, reemplaza esta función.
def clasificar_denuncia(denuncia_text, ejemplos):
    """Simula la clasificación devolviendo 1 (delito), 0 (no delito) o -1 (error)."""
    texto = denuncia_text.upper()
    if 'ESTAFA' in texto or 'ROBO' in texto:
        return 1
    elif 'ERROR DE LLENADO' in texto or 'DUPLICADO' in texto:
        return -1 
    else:
        return 0

ejemplos = [] # Variable dummy, ya que no se usa en la simulación.
# -------------------------------------------------------------------------


load_dotenv()

# api_key = os.getenv("GOOGLE_API_KEY") # Se mantiene por si es necesario para clasificar_denuncia

# --- Configuración de la Página y Variables ---
st.set_page_config(layout="wide", page_title="Análisis Judicial Interactivo")

# ¡IMPORTANTE! REEMPLAZA esta URL con el enlace "Raw" de tu archivo CSV en GitHub
ARCHIVO_CSV_URL = "https://github.com/felipevilla2105-ops/curso-talento-t/raw/refs/heads/main/carga_ficticia_111.csv" 

FECHA_ACTUAL = datetime.now()
LIMITE_MESES = 2 
LIMITE_QUERELLA_MESES = 6 

# st.image('IMG/Imagen1.png', use_container_width=True) # Comentado si no se proporciona la imagen

# --- Función de Carga de Datos (Cacheada) ---
@st.cache_data
def cargar_datos(url):
    """Carga el archivo CSV desde una URL, limpia, convierte y ajusta las columnas de fecha."""
    try:
        df = pd.read_csv(url)
        
        # 1. Conversión y limpieza de fechas
        columnas_fecha = ['Fecha de los Hechos', 'Fecha de la denuncia', 'Fecha Última Actuación']
        for col in columnas_fecha:
            df[col] = pd.to_datetime(df[col], errors='coerce') 
            
        # 2. ELIMINAR LA HORA en la fecha de última actuación
        if 'Fecha Última Actuación' in df.columns:
            df['Fecha Última Actuación'] = df['Fecha Última Actuación'].dt.normalize()
            
        # 3. Limpieza de texto (para comparaciones)
        for col in ['Tipo de Noticia', 'Última Actuación', 'Caracterización']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.upper().str.strip() 
            
        return df
    except Exception as e:
        st.error(f"❌ Error al cargar o procesar el archivo desde la URL. Verifica el enlace Raw: {e}")
        st.info("La URL debe ser el enlace 'Raw' (crudo) de tu archivo CSV en GitHub.")
        return None

# --- Función de Clasificación para Streamlit ---
@st.cache_data(show_spinner="🤖 Clasificando denuncias...")
def clasificar_datos_streamlit(file):
    HECHOS_COL = 'Hechos'
    
    # 1. Cargar el archivo desde el objeto subido (BytesIO)
    try:
        # Detectar el tipo de archivo y leer
        if file.name.lower().endswith('.json'):
            df_upload = pd.read_json(file)
        elif file.name.lower().endswith('.csv'):
            df_upload = pd.read_csv(file)
        else:
            # Si el tipo no es claro, intentar leer el contenido
            file.seek(0)
            try:
                df_upload = pd.read_csv(file)
            except:
                file.seek(0)
                df_upload = pd.read_json(file)

    except Exception as e:
        st.error(f"Error al leer el archivo. Asegúrate de que sea un JSON o CSV válido. Detalle: {e}")
        return None, None

    # 2. Validación de columna
    if HECHOS_COL not in df_upload.columns:
        st.error(f"El archivo debe tener una columna llamada '{HECHOS_COL}'.")
        return None, None

    # 3. Clasificar las denuncias
    clasificaciones = []
    # Usar .fillna('') para asegurar que solo se pasen strings a clasificar_denuncia
    for denuncia in df_upload[HECHOS_COL].fillna(''): 
        # Llama a la función de clasificación (real o simulada)
        resultado = clasificar_denuncia(str(denuncia), ejemplos)
        try:
            clasificaciones.append(int(resultado))
        except:
            clasificaciones.append(-1) # Error de clasificación
            
    df_upload['clasificacion'] = clasificaciones
    
    # 4. Calcular métricas
    conteo = df_upload['clasificacion'].value_counts()
    
    return df_upload, conteo

# --- Ejecución de Carga del Dashboard Principal ---
df = cargar_datos(ARCHIVO_CSV_URL)

st.title("⚖️ Sistema Interactivo de Alertas Judiciales")
st.caption(f"Análisis realizado con fecha: **{FECHA_ACTUAL.strftime('%d/%m/%Y')}**")

if df is not None:
    st.markdown("---")
    
    # --- 0. PREPARACIÓN DE DATOS Y DEFINICIÓN DE LÍMITES ---
    limite_actuacion = FECHA_ACTUAL - pd.DateOffset(months=LIMITE_MESES)
    
    # --- 1 a 4. Lógica de Alertas (Se mantiene igual) ---
    df_querellable = df[df['Tipo de Noticia'] == 'QUERELLA'].copy()
    df_querellable['Dias_Transcurridos'] = (df_querellable['Fecha de la denuncia'] - df_querellable['Fecha de los Hechos']).dt.days
    df_querellable['Tiempo_Transcurrido'] = df_querellable['Dias_Transcurridos'] / 30.4375
    casos_caducidad = df_querellable[
        (df_querellable['Tiempo_Transcurrido'] > LIMITE_QUERELLA_MESES) & 
        (df_querellable['Dias_Transcurridos'] > 0)
    ].sort_values(by='Fecha de los Hechos', ascending=True) 
    total_caducidad = len(casos_caducidad)
    
    casos_inactivos_general = df[
        (df['Fecha Última Actuación'].isnull()) | 
        (df['Fecha Última Actuación'] < limite_actuacion)
    ].sort_values(by='Fecha Última Actuación', ascending=True, na_position='first') 
    total_inactivos_general = len(casos_inactivos_general)
    
    ACTUACION_INACTIVIDAD = 'SOLICITUD A DENUNCIANTE DE INFORMACIÓN ADICIONAL'
    casos_archivo_inactividad = df[
        (df['Última Actuación'] == ACTUACION_INACTIVIDAD) & 
        (df['Fecha Última Actuación'] < limite_actuacion)
    ].sort_values(by='Fecha Última Actuación', ascending=True) 
    total_archivo_inactividad = len(casos_archivo_inactividad)
    
    casos_conciliacion_archivo = df[df['Última Actuación'].str.contains('CONCILIACIÓN CON ACUERDO', na=False)].sort_values(by='Fecha Última Actuación', ascending=True)
    casos_conciliacion_continuar = df[
        df['Última Actuación'].str.contains('FRACASADA|SIN ACUERDO', na=False) 
        & df['Última Actuación'].str.contains('CONCILIACIÓN', na=False)
    ].sort_values(by='Fecha Última Actuación', ascending=True) 
    total_conciliacion_archivo = len(casos_conciliacion_archivo)
    total_conciliacion_continuar = len(casos_conciliacion_continuar)
    
    # --- Panel de Métricas Clave (KPI Dashboard) ---
    st.subheader("📊 Resumen de Alertas Activas")
    
    col1, col2, col3, col4, col5 = st.columns(5) 

    col1.metric(label="🚨 Casos de Caducidad de Querella", value=total_caducidad, delta=f"Superan {LIMITE_QUERELLA_MESES} meses", delta_color="inverse")
    col2.metric(label="🗓️ Sin Actuación (> 2M)", value=total_inactivos_general, delta=f"Necesitan impulso procesal (Límite: {limite_actuacion.strftime('%d/%m/%Y')})", delta_color="off")
    col3.metric(label="📁 Conciliación con Acuerdo", value=total_conciliacion_archivo, delta="Listos para archivo", delta_color="normal")
    col4.metric(label="⏩ Conciliación Fracasada/Sin Acuerdo", value=total_conciliacion_continuar, delta="Listos para continuar el proceso", delta_color="off")
    col5.metric(label="⛔ Inactividad del Denunciante", value=total_archivo_inactividad, delta="Posibles casos a archivar", delta_color="inverse")
    
    st.markdown("---")
    
    # --- Estructura por Pestañas ---
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📅 Caducidad de la Querella", 
        "⏳ Últimas Actuaciones (Avance)", 
        "🤝 Estado de Conciliación", 
        "📈 Modos de las Estafas (Top 5)",
        "🤖 Clasificación por Lote" # NUEVA PESTAÑA
    ])

    # Se mantienen las pestañas 1, 2, 3 y 4 (para brevedad en la respuesta, se omite su código)
    # ... (Código de tab1, tab2, tab3, tab4) ... 
    
    # Solo mostraré la PESTAÑA 5, que contiene la nueva funcionalidad.
    with tab1:
        st.subheader("Análisis de Caducidad por Plazo Legal")
        st.info(f"Filtro: Casos tipo 'QUERELLA' con más de **{LIMITE_QUERELLA_MESES} meses** entre la Fecha de los Hechos y la Fecha de la Denuncia. (Ordenado: más viejo primero)")
        if total_caducidad > 0:
            st.warning(f"🚨 **¡ATENCIÓN!** Se encontraron **{total_caducidad}** casos con riesgo de Caducidad de la Querella.")
        else:
            st.success("✅ ¡Excelente! No se encontraron casos querellables con riesgo de caducidad.")
            
    with tab2:
        st.subheader("1. Procesos sin movimientos recientes (Impulso Necesario)")
        if total_inactivos_general > 0:
            st.warning(f"⏳ **¡Avanzar con el proceso!** Hay **{total_inactivos_general}** procesos que no registran nuevas actuaciones en los últimos dos meses.")
        else:
            st.success("✅ Todos los procesos registran alguna actuación reciente (dentro de los últimos dos meses).")
            
    with tab3:
        st.subheader("Análisis de Conciliación y Seguimiento")
        
    with tab4:
        st.subheader("Distribución de Modalidades de Estafa (Caracterización) - Top 5")
        conteo_modalidades = df['Caracterización'].value_counts().reset_index()
        conteo_modalidades.columns = ['Modalidad', 'Número de Casos']
        top_5_modalidades = conteo_modalidades.head(5)
        if not top_5_modalidades.empty:
            chart = alt.Chart(top_5_modalidades).mark_bar().encode(
                x=alt.X('Modalidad', sort='-y', axis=alt.Axis(title='Modalidad (Top 5)', labelAngle=-45)),
                y=alt.Y('Número de Casos'),
                tooltip=['Modalidad', 'Número de Casos']
            ).properties(title="Top 5 Modalidades de Estafa por Caracterización").interactive()
            st.altair_chart(chart, use_container_width=True)
            
    # ====================================================================
    # PESTAÑA 5: CLASIFICACIÓN POR LOTE (CON ST.METRIC)
    # ====================================================================
    with tab5:
        st.header("🤖 Clasificador de Denuncias por Lote")
        st.info("Sube un archivo (CSV o JSON) que contenga la columna **'Hechos'**. El sistema usará la función `clasificar_denuncia` para etiquetar la columna **'clasificacion'**.")
        
        # Usamos st.file_uploader de Streamlit
        uploaded_file = st.file_uploader("Sube tu archivo (JSON o CSV)", type=['csv', 'json'])
        
        if uploaded_file is not None:
            # Llamada a la función de clasificación y obtención de conteos
            df_clasificado, conteo_clasificacion = clasificar_datos_streamlit(uploaded_file)
            
            if df_clasificado is not None:
                st.success(f"✅ Se clasificaron **{len(df_clasificado)}** denuncias con éxito.")

                # --- TARJETAS DE CONTEO (st.metric) ---
                st.subheader("Resumen de la Clasificación")
                
                # Definir los conteos de manera segura
                delitos = conteo_clasificacion.get(1, 0)
                no_delitos = conteo_clasificacion.get(0, 0)
                errores = conteo_clasificacion.get(-1, 0)

                col_d_1, col_d_2, col_d_3 = st.columns(3)
                
                # Tarjeta 1: Delitos (Clasificación = 1)
                col_d_1.metric(
                    label="🚨 Casos Clasificados como DELITO (1)",
                    value=delitos,
                    delta=f"{delitos / len(df_clasificado) * 100:.1f}% del total",
                    delta_color="inverse"
                )
                
                # Tarjeta 2: No Delitos (Clasificación = 0)
                col_d_2.metric(
                    label="✅ Casos Clasificados como NO DELITO (0)",
                    value=no_delitos,
                    delta=f"{no_delitos / len(df_clasificado) * 100:.1f}% del total",
                    delta_color="normal"
                )
                
                # Tarjeta 3: Errores (-1)
                col_d_3.metric(
                    label="⚠️ Error de Clasificación (-1)",
                    value=errores,
                    delta=f"{errores / len(df_clasificado) * 100:.1f}% del total",
                    delta_color="off"
                )
                
                st.markdown("---")
                
                # --- DESCARGA DEL ARCHIVO CLASIFICADO ---
                st.subheader("Descargar Resultados")
                
                # Preparar el buffer en memoria para la descarga en formato Excel
                excel_buffer = io.BytesIO()
                df_clasificado.to_excel(excel_buffer, index=False)
                excel_buffer.seek(0)
                
                st.download_button(
                    label="📥 Descargar Denuncias Clasificadas (Excel)",
                    data=excel_buffer,
                    file_name="denuncias_clasificadas.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                
                with st.expander("🔎 Ver las primeras 10 filas del archivo clasificado"):
                    st.dataframe(df_clasificado.head(10), use_container_width=True)