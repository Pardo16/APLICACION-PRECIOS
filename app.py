import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Buscador de precios",
    page_icon="🔎",
    layout="centered"
)

st.title("🔎 Buscador de precios")

@st.cache_data
def cargar_excel():
    df = pd.read_excel("tarifa.xlsx")
    df.columns = df.columns.str.strip()
    return df

try:
    df = cargar_excel()

    st.success("Tarifa cargada correctamente")

    nombre = st.text_input("Buscar producto")

    if nombre:
        resultados = df[
            df["Nombre"].astype(str).str.contains(nombre, case=False, na=False)
        ]

        resultados = resultados.dropna(subset=["Precio"])

        if resultados.empty:
            st.warning("No se encontró ningún resultado")
        else:
            st.dataframe(
                resultados[["Nombre", "FORMATO", "Precio"]],
                use_container_width=True
            )

except FileNotFoundError:
    st.error("No encuentro el archivo tarifa.xlsx en la carpeta de la app")