import streamlit as st
import pandas as pd
from pathlib import Path
from urllib.parse import quote

st.set_page_config(page_title="Precios Pescados Pardo", page_icon="🐟", layout="wide")

st.markdown("#### 🐟 Precios Pescados Pardo")

st.markdown("""
<style>
.block-container {padding-top: 1rem; padding-bottom: 1rem;}
div[data-testid="stVerticalBlock"] {gap: 0.35rem;}
p {margin-bottom: 0.15rem;}
hr {margin: 0.35rem 0;}
.stButton button {padding: 0.25rem 0.5rem; font-size: 0.85rem;}
input {font-size: 0.9rem !important;}
</style>
""", unsafe_allow_html=True)


def buscar_excel():
    archivos_excel = list(Path(".").glob("*.xlsx")) + list(Path(".").glob("*.xls"))
    return archivos_excel[0] if archivos_excel else None


def limpiar_precio(valor):
    if pd.isna(valor):
        return None

    if isinstance(valor, (int, float)):
        return float(valor)

    texto = str(valor).strip().replace("€", "").replace(" ", "")

    if "," in texto and "." not in texto:
        texto = texto.replace(",", ".")
    elif "," in texto and "." in texto:
        texto = texto.replace(".", "").replace(",", ".")

    try:
        return float(texto)
    except:
        return None


def euros(valor):
    return f"{float(valor):.2f}".replace(".", ",")


def crear_texto_pedido(nombre_cliente, pedido):
    lineas = ["PEDIDO", f"Cliente: {nombre_cliente}", ""]
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

if "nombre_cliente" not in st.session_state:
    st.session_state.nombre_cliente = ""


nombre_cliente = st.text_input(
    "Cliente",
    value=st.session_state.nombre_cliente,
    placeholder="Nombre del cliente"
)

st.session_state.nombre_cliente = nombre_cliente.strip()

if not st.session_state.nombre_cliente:
    st.warning("Escribe el nombre del cliente para empezar.")
    st.stop()


archivo_excel = buscar_excel()

if archivo_excel is None:
    st.error("No hay ningún Excel en el repositorio.")
    st.stop()


df = pd.read_excel(archivo_excel)
df.columns = df.columns.astype(str).str.strip().str.upper()

columnas_necesarias = ["CODIGO", "DESCRIPCION", "FORMATO", "PRECIO"]
faltan = [col for col in columnas_necesarias if col not in df.columns]

if faltan:
    st.error(f"Faltan columnas: {faltan}")
    st.write("Columnas encontradas:", list(df.columns))
    st.stop()

df["PRECIO"] = df["PRECIO"].apply(limpiar_precio)
df = df.dropna(subset=["PRECIO"])

df["CLIENTE FINAL"] = df["PRECIO"] / 0.55
df["ALTA DISTRIBUCION"] = df["PRECIO"] / 0.90
df["HOSTELERIA"] = df["PRECIO"] / 0.80

for col in ["PRECIO", "CLIENTE FINAL", "ALTA DISTRIBUCION", "HOSTELERIA"]:
    df[col] = df[col].round(2)


# Pedido arriba
if st.session_state.pedido:
    total_cajas = sum(item["cajas"] for item in st.session_state.pedido)
    st.success(
        f"Pedido | Cliente: {st.session_state.nombre_cliente} | "
        f"Productos: {len(st.session_state.pedido)} | Cajas: {total_cajas}"
    )

    texto_pedido = crear_texto_pedido(st.session_state.nombre_cliente, st.session_state.pedido)
    whatsapp_url = "https://wa.me/?text=" + quote(texto_pedido)

    col_a, col_b, col_c = st.columns([1, 1, 1])

    with col_a:
        st.link_button("✅ Finalizar pedido", whatsapp_url)

    with col_b:
        with st.expander("Ver pedido"):
            st.text(texto_pedido)

    with col_c:
        if st.button("Vaciar pedido"):
            st.session_state.pedido = []
            st.rerun()
else:
    st.info(f"Pedido vacío | Cliente: {st.session_state.nombre_cliente}")


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

busqueda = st.text_input("Buscar producto", placeholder="Ej: anilla, atún, calamar...")

if busqueda:
    resultados = df[
        df["DESCRIPCION"].astype(str).str.contains(busqueda, case=False, na=False)
    ].reset_index(drop=True)

    if resultados.empty:
        st.warning("No se encontró ningún producto")
    else:
        for i, fila in resultados.iterrows():
            codigo = str(fila["CODIGO"])
            descripcion = str(fila["DESCRIPCION"])
            formato = str(fila["FORMATO"])
            precio = float(fila[columna_precio])

            col_info, col_cajas, col_add = st.columns([6, 1, 1])

            with col_info:
                st.markdown(
                    f"<div style='font-size:0.85rem; line-height:1.1;'>"
                    f"<b>{descripcion}</b><br>"
                    f"{euros(precio)} € · {formato}"
                    f"</div>",
                    unsafe_allow_html=True
                )

            with col_cajas:
                cajas = st.number_input(
                    "Cajas",
                    min_value=1,
                    value=1,
                    step=1,
                    key=f"cajas_{i}_{codigo}_{tarifa}",
                    label_visibility="collapsed"
                )

            with col_add:
                if st.button("➕", key=f"add_{i}_{codigo}_{tarifa}"):
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
