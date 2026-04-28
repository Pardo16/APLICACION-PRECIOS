import streamlit as st
import pandas as pd
from pathlib import Path
from urllib.parse import quote

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
    return f"{float(valor):.2f}".replace(".", ",")

def crear_texto_pedido(pedido):
    lineas = ["PEDIDO", ""]
    total_cajas = 0

    for item in pedido:
        total_cajas += item["cajas"]
        lineas.append(
            f"- {item['cajas']} cajas | {item['descripcion']} | "
            f"{euros(item['precio'])} € | {item['formato']}"
        )

    lineas.append("")
    lineas.append(f"Total cajas: {total_cajas}")
    return "\n".join(lineas)

if "pedido" not in st.session_state:
    st.session_state.pedido = []

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
        df["PRECIO"] = df["PRECIO"].apply(limpiar_precio)
        df = df.dropna(subset=["PRECIO"])

        df["CLIENTE FINAL"] = df["PRECIO"] / 0.55
        df["ALTA DISTRIBUCION"] = df["PRECIO"] / 0.90
        df["HOSTELERIA"] = df["PRECIO"] / 0.80

        for col in ["PRECIO", "CLIENTE FINAL", "ALTA DISTRIBUCION", "HOSTELERIA"]:
            df[col] = df[col].round(2)

        st.markdown("## 🧾 Pedido")

        if not st.session_state.pedido:
            st.info("Pedido vacío")
        else:
            total_cajas = sum(item["cajas"] for item in st.session_state.pedido)

            st.success(f"Productos añadidos: {len(st.session_state.pedido)} | Total cajas: {total_cajas}")

            with st.expander("Ver pedido"):
                for item in st.session_state.pedido:
                    st.write(
                        f"{item['cajas']} cajas | {item['descripcion']} | "
                        f"{euros(item['precio'])} € | {item['formato']}"
                    )

            texto_pedido = crear_texto_pedido(st.session_state.pedido)
            whatsapp_url = "https://wa.me/?text=" + quote(texto_pedido)

            st.link_button("✅ Finalizar pedido por WhatsApp", whatsapp_url)

            if st.button("Vaciar pedido"):
                st.session_state.pedido = []
                st.rerun()

        st.markdown("---")

        tarifa = st.radio(
            "Tarifa",
            ["Coste", "Cliente final", "Alta distribución", "Hostelería"],
            horizontal=True
        )

        columna_precio = {
            "Coste": "PRECIO",
            "Cliente final": "CLIENTE FINAL",
            "Alta distribución": "ALTA DISTRIBUCION",
            "Hostelería": "HOSTELERIA",
        }[tarifa]

        busqueda = st.text_input("Buscar producto")

        if busqueda:
            resultados = df[
                df["DESCRIPCION"].astype(str).str.contains(busqueda, case=False, na=False)
            ]

            if resultados.empty:
                st.warning("No se encontró ningún producto")
            else:
                st.markdown("### Resultados")

                for i, fila in resultados.reset_index(drop=True).iterrows():
                    codigo = str(fila["CODIGO"])
                    descripcion = str(fila["DESCRIPCION"])
                    formato = str(fila["FORMATO"])
                    precio = float(fila[columna_precio])

                    col_info, col_cajas, col_add = st.columns([5, 1.4, 1.6])

                    with col_info:
                        st.markdown(
                            f"**{descripcion}**  \n"
                            f"{euros(precio)} € · {formato}"
                        )

                    with col_cajas:
                        cajas = st.number_input(
                            "Cajas",
                            min_value=1,
                            value=1,
                            step=1,
                            key=f"cajas_{i}_{codigo}_{tarifa}"
                        )

                    with col_add:
                        st.write("")
                        if st.button("Añadir", key=f"add_{i}_{codigo}_{tarifa}"):
                            st.session_state.pedido.append({
                                "cajas": int(cajas),
                                "codigo": codigo,
                                "descripcion": descripcion,
                                "precio": precio,
                                "formato": formato,
                                "tarifa": tarifa,
                            })
                            st.rerun()

                    st.markdown("---")
