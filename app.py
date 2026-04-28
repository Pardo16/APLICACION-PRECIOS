import streamlit as st
import pandas as pd
from pathlib import Path

st.set_page_config(
    page_title="Buscador de precios PRO",
    page_icon="🔎",
    layout="centered"
)

st.title("🔎 Buscador de precios PRO")

# 🔍 Buscar Excel automáticamente
def buscar_excel():
    archivos_excel = list(Path(".").glob("*.xlsx")) + list(Path(".").glob("*.xls"))
    return archivos_excel[0] if archivos_excel else None


# 💰 Limpiar precios
def limpiar_precio(valor):
    if pd.isna(valor):
        return None

    if isinstance(valor, (int, float)):
        return float(valor)

    texto = str(valor).strip()
    texto = texto.replace("€", "").replace(" ", "")

    if "," in texto and "." not in texto:
        texto = texto.replace(",", ".")
    elif "," in texto and "." in texto:
        texto = texto.replace(".", "")
        texto = texto.replace(",", ".")

    try:
        return float(texto)
    except:
        return None


archivo_excel = buscar_excel()

if archivo_excel is None:
    st.error("No hay ningún Excel en el repositorio.")
else:
    st.info(f"Usando archivo: {archivo_excel.name}")

    df = pd.read_excel(archivo_excel)
    df.columns = df.columns.astype(str).str.strip().str.upper()

    columnas_necesarias = ["CODIGO", "DESCRIPCION", "FORMATO", "PRECIO"]
    faltan = [col for col in columnas_necesarias if col not in df.columns]

    if faltan:
        st.error(f"Faltan columnas: {faltan}")
        st.write("Columnas encontradas:", list(df.columns))
    else:
        # Limpieza precios
        df["PRECIO"] = df["PRECIO"].apply(limpiar_precio)
        df = df.dropna(subset=["PRECIO"])

        # Cálculos
        df["CLIENTE FINAL"] = df["PRECIO"] / 0.55
        df["ALTA DISTRIBUCION"] = df["PRECIO"] / 0.90
        df["HOSTELERIA"] = df["PRECIO"] / 0.80

        for col in ["PRECIO", "CLIENTE FINAL", "ALTA DISTRIBUCION", "HOSTELERIA"]:
            df[col] = df[col].round(2)

        st.success("Tarifa cargada correctamente")

        # 🔘 Selector tipo precio
        tipo_precio = st.radio(
            "Selecciona tarifa",
            ["Coste", "Cliente final", "Alta distribución", "Hostelería", "Todo"],
            horizontal=True
        )

        # 🔎 Buscador
        busqueda = st.text_input("Buscar producto")

        if busqueda:
            resultados = df[
                df["DESCRIPCION"].astype(str).str.contains(busqueda, case=False, na=False)
            ]

            if resultados.empty:
                st.warning("No se encontró ningún producto")
            else:
                columnas_map = {
                    "Coste": ["CODIGO", "DESCRIPCION", "PRECIO", "FORMATO"],
                    "Cliente final": ["CODIGO", "DESCRIPCION", "CLIENTE FINAL", "FORMATO"],
                    "Alta distribución": ["CODIGO", "DESCRIPCION", "ALTA DISTRIBUCION", "FORMATO"],
                    "Hostelería": ["CODIGO", "DESCRIPCION", "HOSTELERIA", "FORMATO"],
                    "Todo": [
                        "CODIGO",
                        "DESCRIPCION",
                        "PRECIO",
                        "CLIENTE FINAL",
                        "ALTA DISTRIBUCION",
                        "HOSTELERIA",
                        "FORMATO",
                    ],
                }

                columnas_mostrar = columnas_map[tipo_precio]

                st.dataframe(
                    resultados[columnas_mostrar],
                    use_container_width=True,
                    hide_index=True
                )
