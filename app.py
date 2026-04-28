import streamlit as st
import pandas as pd
from pathlib import Path
from urllib.parse import quote

st.set_page_config(page_title="Precios Pescados Pardo", page_icon="🐟", layout="wide")

st.markdown("#### 🐟 Precios Pescados Pardo")

st.markdown("""
<style>
.block-container {padding-top: 1rem; padding-bottom: 1rem;}
div[data-testid="stVerticalBlock"] {gap: 0.25rem;}
hr {margin: 0.25rem 0;}
.stButton button {padding: 0.2rem 0.4rem; font-size: 0.8rem;}
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

if "mensaje" not in st.session_state:
    st.session_state.mensaje = ""


# Cliente
nombre_cliente = st.text_input("Cliente", value=st.session_state.nombre_cliente)
st.session_state.nombre_cliente = nombre_cliente.strip()

if not st.session_state.nombre_cliente:
    st.warning("Escribe el nombre del cliente")
    st.stop()


archivo_excel = buscar_excel()
if archivo_excel is None:
    st.error("No hay Excel en el repo")
    st.stop()

df = pd.read_excel(archivo_excel)
df.columns = df.columns.astype(str).str.strip().str.upper()

df["PRECIO"] = df["PRECIO"].apply(limpiar_precio)
df = df.dropna(subset=["PRECIO"])

df["CLIENTE FINAL"] = df["PRECIO"] / 0.55
df["ALTA DISTRIBUCION"] = df["PRECIO"] / 0.90
df["HOSTELERIA"] = df["PRECIO"] / 0.80

for col in ["PRECIO", "CLIENTE FINAL", "ALTA DISTRIBUCION", "HOSTELERIA"]:
    df[col] = df[col].round(2)


# Pedido
if st.session_state.pedido:
    total = sum(i["cajas"] for i in st.session_state.pedido)

    st.success(f"{len(st.session_state.pedido)} productos | {total} cajas")

    texto = crear_texto_pedido(st.session_state.nombre_cliente, st.session_state.pedido)
    url = "https://wa.me/?text=" + quote(texto)

    col1, col2 = st.columns([1,1])

    with col1:
        st.link_button("Finalizar pedido", url)

    with col2:
        if st.button("Vaciar"):
            st.session_state.pedido = []
            st.rerun()

# Mensaje de feedback
if st.session_state.mensaje:
    st.success(st.session_state.mensaje)
    st.session_state.mensaje = ""


tarifa = st.radio(
    "Tarifa",
    ["Coste", "Cliente final", "Alta distribución", "Hostelería"],
    horizontal=True
)

col_precio = {
    "Coste": "PRECIO",
    "Cliente final": "CLIENTE FINAL",
    "Alta distribución": "ALTA DISTRIBUCION",
    "Hostelería": "HOSTELERIA",
}[tarifa]

busqueda = st.text_input("Buscar")

if busqueda:
    resultados = df[
        df["DESCRIPCION"].astype(str).str.contains(busqueda, case=False, na=False)
    ].reset_index(drop=True)

    for i, fila in resultados.iterrows():
        descripcion = fila["DESCRIPCION"]
        formato = fila["FORMATO"]
        precio = fila[col_precio]

        col1, col2 = st.columns([7, 2])

        with col1:
            st.markdown(
                f"<b>{descripcion}</b> · {euros(precio)} € · {formato}",
                unsafe_allow_html=True
            )

        with col2:
            sub1, sub2 = st.columns([1,1])

            with sub1:
                cajas = st.number_input(
                    "",
                    min_value=1,
                    value=1,
                    step=1,
                    key=f"c_{i}",
                    label_visibility="collapsed"
                )

            with sub2:
                if st.button("➕", key=f"a_{i}"):
                    st.session_state.pedido.append({
                        "cajas": int(cajas),
                        "descripcion": descripcion,
                        "precio": precio,
                        "formato": formato
                    })
                    st.session_state.mensaje = f"✔ {descripcion} añadido"
                    st.rerun()

        st.markdown("---")
