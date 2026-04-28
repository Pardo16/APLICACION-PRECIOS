import streamlit as st
import pandas as pd
from pathlib import Path

st.set_page_config(
    page_title="Buscador de precios PRO",
    page_icon="🔎",
    layout="centered"
)

st.title("🔎 Buscador de precios PRO")

def buscar_excel():
    archivos_excel = list(Path(".").glob("*.xlsx")) + list(Path(".").glob("*.xls"))
    return archivos_excel[0] if archivos_excel else None

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

def euros(valor):
    return f"{valor:.2f} €".replace(".", ",")

archivo_excel = buscar_excel()

if archivo_excel is None:
    st.error("No hay ningún archivo Excel en el repositorio.")
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
        df["PRECIO"] = df["PRECIO"].apply(limpiar_precio)
        df = df.dropna(subset=["PRECIO"])

        df["CLIENTE FINAL"] = df["PRECIO"] / 0.55
        df["ALTA DISTRIBUCION"] = df["PRECIO"] / 0.90
        df["HOSTELERIA"] = df["PRECIO"] / 0.80

        for col in ["PRECIO", "CLIENTE FINAL", "ALTA DISTRIBUCION", "HOSTELERIA"]:
            df[col] = df[col].round(2)

        st.success("Tarifa cargada correctamente")

        tipo_precio = st.radio(
            "Selecciona tarifa",
            ["Coste", "Cliente final", "Alta distribución", "Hostelería", "Todo"],
            horizontal=True
        )

        busqueda = st.text_input("Buscar producto")

        if busqueda:
            resultados = df[
                df["DESCRIPCION"].astype(str).str.contains(busqueda, case=False, na=False)
            ]

            if resultados.empty:
                st.warning("No se encontró ningún producto")
            else:
                columna_precio = {
                    "Coste": "PRECIO",
                    "Cliente final": "CLIENTE FINAL",
                    "Alta distribución": "ALTA DISTRIBUCION",
                    "Hostelería": "HOSTELERIA",
                }

                if tipo_precio != "Todo":
                    col = columna_precio[tipo_precio]

                    for _, fila in resultados.iterrows():
                        st.markdown("---")
                        st.subheader(str(fila["DESCRIPCION"]))

                        st.write(f"**Código:** {fila['CODIGO']}")
                        st.write(f"**Formato:** {fila['FORMATO']}")

                        st.markdown(
                            f"""
                            <div style="
                                font-size:42px;
                                font-weight:800;
                                padding:18px;
                                border-radius:18px;
                                background:#f1f1f1;
                                text-align:center;
                                margin-top:10px;
                            ">
                                {euros(fila[col])}
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

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
