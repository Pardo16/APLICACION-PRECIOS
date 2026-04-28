import streamlit as st
import pandas as pd
from pathlib import Path

st.set_page_config(
    page_title="Buscador de precios PRO",
    page_icon="🔎",
    layout="centered"
)

st.title("🔎 Buscador de precios PRO")

# 🔍 Buscar automáticamente Excel en el repo
def buscar_excel():
    archivos_excel = list(Path(".").glob("*.xlsx")) + list(Path(".").glob("*.xls"))
    if not archivos_excel:
        return None
    return archivos_excel[0]


# 💰 Limpiar precios correctamente
def limpiar_precio(valor):
    if pd.isna(valor):
        return None

    if isinstance(valor, (int, float)):
        return float(valor)

    texto = str(valor).strip()
    texto = texto.replace("€", "").replace(" ", "")

    # Caso español: 10,8 → 10.8
    if "," in texto and "." not in texto:
        texto = texto.replace(",", ".")

    # Caso miles: 1.234,56 → 1234.56
    elif "," in texto and "." in texto:
        texto = texto.replace(".", "")
        texto = texto.replace(",", ".")

    try:
        return float(texto)
    except:
        return None


archivo_excel = buscar_excel()

if archivo_excel is None:
    st.error("No hay ningún archivo Excel en el repositorio.")
else:
    st.info(f"Usando archivo: {archivo_excel.name}")

    df = pd.read_excel(archivo_excel)

    # 🔧 Limpiar nombres de columnas
    df.columns = df.columns.astype(str).str.strip().str.upper()

    columnas_necesarias = ["CODIGO", "DESCRIPCION", "FORMATO", "PRECIO"]
    faltan = [col for col in columnas_necesarias if col not in df.columns]

    if faltan:
        st.error(f"Faltan columnas: {faltan}")
        st.write("Columnas encontradas:", list(df.columns))
    else:
        # Limpiar precios
        df["PRECIO"] = df["PRECIO"].apply(limpiar_precio)
        df = df.dropna(subset=["PRECIO"])

        # 💸 Cálculo de precios
        df["CLIENTE FINAL"] = df["PRECIO"] / 0.55
        df["ALTA DISTRIBUCION"] = df["PRECIO"] / 0.90
        df["HOSTELERIA"] = df["PRECIO"] / 0.80

        # Redondeo
        for col in ["PRECIO", "CLIENTE FINAL", "ALTA DISTRIBUCION", "HOSTELERIA"]:
            df[col] = df[col].round(2)

        st.success("Tarifa cargada correctamente")

        # 🔎 Buscador
        busqueda = st.text_input("Buscar producto")

        if busqueda:
            resultados = df[
                df["DESCRIPCION"].astype(str).str.contains(busqueda, case=False, na=False)
            ]

            if resultados.empty:
                st.warning("No se encontró ningún producto")
            else:
                tab_coste, tab_cliente, tab_distribucion, tab_hosteleria, tab_todo = st.tabs(
                    ["Coste", "Cliente final", "Alta distribución", "Hostelería", "Todo"]
                )

                with tab_coste:
                    st.dataframe(
                        resultados[["CODIGO", "DESCRIPCION", "FORMATO", "PRECIO"]],
                        use_container_width=True,
                        hide_index=True
                    )

                with tab_cliente:
                    st.dataframe(
                        resultados[["CODIGO", "DESCRIPCION", "FORMATO", "CLIENTE FINAL"]],
                        use_container_width=True,
                        hide_index=True
                    )

                with tab_distribucion:
                    st.dataframe(
                        resultados[["CODIGO", "DESCRIPCION", "FORMATO", "ALTA DISTRIBUCION"]],
                        use_container_width=True,
                        hide_index=True
                    )

                with tab_hosteleria:
                    st.dataframe(
                        resultados[["CODIGO", "DESCRIPCION", "FORMATO", "HOSTELERIA"]],
                        use_container_width=True,
                        hide_index=True
                    )

                with tab_todo:
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
