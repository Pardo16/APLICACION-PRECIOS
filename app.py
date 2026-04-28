import streamlit as st
import pandas as pd
from pathlib import Path
from urllib.parse import quote

st.set_page_config(page_title="Precios Pescados Pardo", page_icon="🐟", layout="centered")

st.markdown("""
<style>

/* 🔵 FONDO TURQUESA */
.stApp {
    background-color: #d8f5f2;
    color: black;
}

/* TEXTO NEGRO */
h1, h2, h3, h4, h5, h6, p, div, span {
    color: black !important;
}

/* INPUT VERDE */
div[data-baseweb="input"] input {
    border: 2px solid #28a745 !important;
    background-color: white !important;
    color: black !important;
}

div[data-baseweb="input"] input:focus {
    border: 2px solid #28a745 !important;
    box-shadow: 0 0 0 1px #28a745 !important;
}

/* BOTONES */
.stButton button {
    background-color: white;
    color: black;
    border-radius: 8px;
}

/* PRODUCTO */
.producto {
    font-size: 0.9rem;
    line-height: 1.2;
    margin-bottom: 0.25rem;
}

/* ESPACIADO */
.block-container {
    padding-top: 0.5rem;
    padding-bottom: 0.5rem;
}

hr {
    margin: 0.35rem 0;
}

</style>
""", unsafe_allow_html=True)

st.markdown("#### 🐟 Precios Pescados Pardo")


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
    total = 0

    for item in pedido:
        total += item["cajas"]
        lineas.append(
            f"- {item['cajas']} cajas | {item['descripcion']} | "
            f"{euros(item['precio'])} € | {item['formato']}"
        )

    lineas.append("")
    lineas.append(f"Total cajas: {total}")
    return "\n".join(lineas)


if "pedido" not in st.session_state:
    st.session_state.pedido = []

if "productos_anadidos" not in st.session_state:
    st.session_state.productos_anadidos = set()

if "ver_pedido" not in st.session_state:
    st.session_state.ver_pedido = False


nombre_cliente = st.text_input("Cliente")

if not nombre_cliente:
    st.warning("Escribe el nombre del cliente")
    st.stop()


archivo = buscar_excel()

if archivo is None:
    st.error("No hay Excel en el repositorio")
    st.stop()


df = pd.read_excel(archivo)
df.columns = df.columns.astype(str).str.strip().str.upper()

df["PRECIO"] = df["PRECIO"].apply(limpiar_precio)
df = df.dropna(subset=["PRECIO"]).reset_index(drop=True)

df["CLIENTE FINAL"] = df["PRECIO"] / 0.55
df["ALTA DISTRIBUCION"] = df["PRECIO"] / 0.90
df["HOSTELERIA"] = df["PRECIO"] / 0.80


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


# 🔥 PEDIDO
if st.session_state.pedido:
    total = sum(i["cajas"] for i in st.session_state.pedido)

    st.success(f"{len(st.session_state.pedido)} productos | {total} cajas")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Ver pedido"):
            st.session_state.ver_pedido = not st.session_state.ver_pedido
            st.rerun()

    with col2:
        texto = crear_texto_pedido(nombre_cliente, st.session_state.pedido)
        url = "https://wa.me/?text=" + quote(texto)
        st.link_button("Finalizar", url)

    with col3:
        if st.button("Vaciar"):
            st.session_state.pedido = []
            st.session_state.productos_anadidos = set()
            st.session_state.ver_pedido = False
            st.rerun()

    if st.session_state.ver_pedido:
        texto = crear_texto_pedido(nombre_cliente, st.session_state.pedido)
        st.text_area("Pedido", texto, height=200)

        if st.button("Continuar"):
            st.session_state.ver_pedido = False
            st.rerun()


# 🔍 BUSCADOR
busqueda = st.text_input("Buscar (opcional)")

if busqueda:
    resultados = df[df["DESCRIPCION"].str.contains(busqueda, case=False, na=False)]
else:
    resultados = df.copy()

resultados = resultados.sort_values("DESCRIPCION").reset_index(drop=True)


# 🔥 PRODUCTOS SIEMPRE VISIBLES
for i, fila in resultados.iterrows():
    descripcion = fila["DESCRIPCION"]
    formato = fila["FORMATO"]
    precio = fila[col_precio]

    key_add = f"add_{i}"

    st.markdown(
        f"<div class='producto'><b>{descripcion}</b> · {euros(precio)} € · {formato}</div>",
        unsafe_allow_html=True
    )

    col1, col2 = st.columns([1, 1])

    with col1:
        cajas = st.number_input(
            "Cajas",
            min_value=1,
            value=1,
            step=1,
            key=f"cajas_{i}",
            label_visibility="collapsed"
        )

    with col2:
        texto = "Añadido" if key_add in st.session_state.productos_anadidos else "Añadir"

        if st.button(texto, key=key_add):
            st.session_state.pedido.append({
                "cajas": int(cajas),
                "descripcion": descripcion,
                "precio": precio,
                "formato": formato
            })
            st.session_state.productos_anadidos.add(key_add)
            st.rerun()

    st.markdown("---")
