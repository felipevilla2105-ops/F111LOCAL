import streamlit as st
import pandas as pd
from datetime import datetime
import altair as alt 
from dotenv import load_dotenv
import os

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")

#print

# --- Configuración de la Página y Variables ---
st.set_page_config(layout="wide", page_title="Análisis Judicial Interactivo")

# ¡IMPORTANTE! REEMPLAZA esta URL con el enlace "Raw" de tu archivo CSV en GitHub
ARCHIVO_CSV_URL = "https://github.com/felipevilla2105-ops/curso-talento-t/raw/refs/heads/main/carga_ficticia_111.csv" 

FECHA_ACTUAL = datetime.now()
LIMITE_MESES = 2 # Límite de meses para Inactividad y Últimas Actuaciones
LIMITE_QUERELLA_MESES = 6 # Límite de meses para Caducidad

st.image('IMG/Imagen4.png', use_container_width=True)

# --- Función de Carga de Datos (Cacheada) ---
@st.cache_data
def cargar_datos(url):
    """Carga el archivo CSV desde una URL, limpia y convierte las columnas de fecha."""
    try:
        df = pd.read_csv(url)
        
        # 1. Conversión y limpieza de fechas
        columnas_fecha = ['Fecha de los Hechos', 'Fecha de la denuncia', 'Fecha Última Actuación']
        for col in columnas_fecha:
            # Intentar convertir al formato datetime, forzando NaT en caso de error
            df[col] = pd.to_datetime(df[col], errors='coerce') 
            
        # 2. Limpieza de texto (para comparaciones)
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
    
    # Límite de fecha para actuaciones (2 meses atrás)
    limite_actuacion = FECHA_ACTUAL - pd.DateOffset(months=LIMITE_MESES)
    
    # --- 1. CADUCIDAD DE LA QUERELLA ---
    df_querellable = df[df['Tipo de Noticia'] == 'QUERELLA'].copy()
    
    # Calcular diferencia en días (solo si la denuncia es posterior o igual a los hechos)
    df_querellable['Dias_Transcurridos'] = (df_querellable['Fecha de la denuncia'] - df_querellable['Fecha de los Hechos']).dt.days
    df_querellable['Tiempo_Transcurrido'] = df_querellable['Dias_Transcurridos'] / 30.4375
    
    # Filtrar casos que superan el límite (y donde la diferencia es positiva)
    casos_caducidad = df_querellable[
        (df_querellable['Tiempo_Transcurrido'] > LIMITE_QUERELLA_MESES) & 
        (df_querellable['Dias_Transcurridos'] > 0)
    ]
    total_caducidad = len(casos_caducidad)
    
    # --- 2. INACTIVIDAD GENERAL ---
    casos_inactivos_general = df[
        (df['Fecha Última Actuación'].isnull()) | 
        (df['Fecha Última Actuación'] < limite_actuacion)
    ]
    total_inactivos_general = len(casos_inactivos_general)
    
    # --- 3. INACTIVIDAD DEL DENUNCIANTE (CORRECCIÓN APLICADA) ---
    ACTUACION_INACTIVIDAD = 'SOLICITUD A DENUNCIANTE DE INFORMACIÓN ADICIONAL'
    
    # Filtrar casos con la actuación específica Y más de 2 meses sin movimiento
    casos_archivo_inactividad = df[
        (df['Última Actuación'] == ACTUACION_INACTIVIDAD) & 
        (df['Fecha Última Actuación'] < limite_actuacion)
    ]
    total_archivo_inactividad = len(casos_archivo_inactividad)
    
    # --- 4. CONCILIACIÓN ---
    casos_conciliacion_archivo = df[df['Última Actuación'].str.contains('CONCILIACIÓN CON ACUERDO', na=False)]
    casos_conciliacion_continuar = df[df['Última Actuación'].str.contains('CONCILIACIÓN (FRACASADA|SIN ACUERDO)', na=False)]
    total_conciliacion_archivo = len(casos_conciliacion_archivo)
    total_conciliacion_continuar = len(casos_conciliacion_continuar)
    
    
    # --- Panel de Métricas Clave (KPI Dashboard) ---
    st.subheader("📊 Resumen de Alertas Activas")
    
    col1, col2, col3, col4 = st.columns(4)

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
        "📈 Modos de las Estafas"
    ])

    # ====================================================================
    # PESTAÑA 1: CADUCIDAD DE LA QUERELLA
    # ====================================================================
    with tab1:
        st.subheader("Análisis de Caducidad por Plazo Legal")
        st.info(f"Filtro: Casos tipo 'QUERELLA' con más de **{LIMITE_QUERELLA_MESES} meses** entre la Fecha de los Hechos y la Fecha de la Denuncia.")

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
        st.info(f"Filtro: Casos cuya 'Fecha Última Actuación' es anterior al **{limite_actuacion.strftime('%d/%m/%Y')}** (más de {LIMITE_MESES} meses).")
        
        if total_inactivos_general > 0:
            st.warning(f"⏳ **¡Avanzar con el proceso!** Hay **{total_inactivos_general}** procesos que no registran nuevas actuaciones en los últimos dos meses.")
            
            with st.expander("🔎 Ver Procesos Inactivos (General)"):
                df_mostrar = casos_inactivos_general[['Caso Noticia', 'Fecha Última Actuación', 'Última Actuación']]
                st.dataframe(df_mostrar, use_container_width=True)
        else:
            st.success("✅ Todos los procesos registran alguna actuación reciente (dentro de los últimos dos meses).")
            
        st.markdown("---")
            
        st.subheader("2. Inactividad del Denunciante (Sugerencia de Archivo)")
        st.info(f"Filtro: Casos con 'Última Actuación' = **{ACTUACION_INACTIVIDAD}** y esta es anterior al **{limite_actuacion.strftime('%d/%m/%Y')}**.")
        
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
        
        col_c_1, col_c_2 = st.columns(2)

        # 3.1. Conciliación con Acuerdo (Archivo)
        with col_c_1:
            st.markdown("##### Casos con Acuerdo")
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
            st.markdown("##### Casos Sin Acuerdo/Fracasada")
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
    # PESTAÑA 4: MODOS DE LA ESTAFAS (GRÁFICA)
    # ====================================================================
    with tab4:
        st.subheader("Distribución de Modalidades de Estafa (Caracterización)")
        st.markdown("Este gráfico muestra las modalidades de estafa más frecuentes para establecer patrones.")

        conteo_modalidades = df['Caracterización'].value_counts().reset_index()
        conteo_modalidades.columns = ['Modalidad', 'Número de Casos']
        
        if not conteo_modalidades.empty:
            # Uso de Altair para un gráfico más interactivo
            chart = alt.Chart(conteo_modalidades.head(10)).mark_bar().encode(
                x=alt.X('Modalidad', sort='-y', axis=alt.Axis(title='Modalidad (Top 10)', labelAngle=-45)),
                y=alt.Y('Número de Casos'),
                tooltip=['Modalidad', 'Número de Casos']
            ).properties(
                title="Top 10 Modalidades de Estafa por Caracterización"
            ).interactive()
            
            st.altair_chart(chart, use_container_width=True)

            with st.expander("Ver tabla completa de Modalidades"):
                st.dataframe(conteo_modalidades, use_container_width=True)

        else:
            st.warning("No hay datos válidos en la columna 'Caracterización' para generar la gráfica.")