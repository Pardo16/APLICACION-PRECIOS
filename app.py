import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Buscador de precios PRO",
    page_icon="🔎",
    layout="centered"
)

st.title("🔎 Buscador de precios PRO")

archivo = st.file_uploader("Sube tu Excel", type=["xlsx", "xls"])

def limpiar_precio(valor):
    if pd.isna(valor):
        return None

    texto = str(valor).strip()
    texto = texto.replace("€", "")
    texto = texto.replace(".", "")
    texto = texto.replace(",", ".")

    try:
        return float(texto)
    except:
        return None


if archivo is not None:
    try:
        df = pd.read_excel(archivo)

        df.columns = df.columns.astype(str).str.strip().str.upper()

        columnas_necesarias = ["CODIGO", "DESCRIPCION", "FORMATO", "PRECIO"]

        faltan = [col for col in columnas_necesarias if col not in df.columns]

        if faltan:
            st.error(f"Faltan columnas: {faltan}")
            st.write("Columnas encontradas:", list(df.columns))

        else:
            df["PRECIO"] = df["PRECIO"].apply(limpiar_precio)
            df = df.dropna(subset=["PRECIO"])

            df["CLIENTE FINAL"] = df["PRECIO"] / 0.55
            df["ALTA DISTRIBUCION"] = df["PRECIO"] / 0.90
            df["HOSTELERIA"] = df["PRECIO"] / 0.80

            for col in ["PRECIO", "CLIENTE FINAL", "ALTA DISTRIBUCION", "HOSTELERIA"]:
                df[col] = df[col].round(2)

            st.success("Excel cargado correctamente")

            busqueda = st.text_input("Buscar producto")

            if busqueda:
                resultados = df[
                    df["DESCRIPCION"].astype(str).str.contains(busqueda, case=False, na=False)
                ]

                if resultados.empty:
                    st.warning("No se encontró nada")
                else:
                    st.dataframe(
                        resultados[
                            [
                                "CODIGO",
                                "DESCRIPCION",
                                "FORMATO",
                                "PRECIO",
                                "CLIENTE FINAL",
                                "ALTA DISTRIBUCION",
                                "HOSTELERIA",
                            ]
                        ],
                        use_container_width=True,
                        hide_index=True
                    )

    except Exception as e:
        st.error(f"Error al cargar el Excel: {e}")
