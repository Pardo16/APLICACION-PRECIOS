import streamlit as st
import pandas as pd
from pathlib import Path
from urllib.parse import quote

st.set_page_config(page_title="Precios Pescados Pardo", page_icon="🐟", layout="centered")

st.markdown("#### 🐟 Precios Pescados Pardo")

st.markdown("""
<style>
.block-container {padding-top: 0.6rem; padding-bottom: 0.6rem;}
div[data-testid="stVerticalBlock"] {gap: 0.35rem;}
hr {margin: 0.5rem 0;}

.producto {
    font-size: 0.88rem;
    line-height: 1.2;
    margin-bottom: 0.3rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.stButton button {
    padding: 0.25rem 0.5rem;
    font-size: 0.85rem;
}
</style>
""", unsafe_allow_html=True)


# =========================
# TARIFAS
# =========================

TARIFAS = {
    "1": "PRECIO",
    "2": "CLIENTE FINAL",
    "3": "ALTA DISTRIBUCION",
    "4": "HOSTELERIA",
}


# =========================
# FUNCIONES
# =========================

def buscar_excel_tarifa():
    archivos = list(Path(".").glob("*.xlsx")) + list(Path(".").glob("*.xls"))
    archivos = [a for a in archivos if a.name.lower() != "clientes.xlsx"]
    return archivos[0] if archivos else None


def buscar_excel_clientes():
    archivo = Path("clientes.xlsx")
    return archivo if archivo.exists() else None


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


def crear_texto_pedido(cliente, pedido):
    lineas = ["PEDIDO", f"Cliente: {cliente}", ""]
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


def cargar_clientes():
    archivo = buscar_excel_clientes()

    if archivo is None:
        st.error("No hay clientes.xlsx")
        st.stop()

    clientes = pd.read_excel(archivo)
    clientes.columns = clientes.columns.str.strip().str.upper()

    clientes["N_CLIENTE"] = clientes["N_CLIENTE"].astype(str).str.strip()
    clientes["CONTRASEÑA"] = clientes["CONTRASEÑA"].astype(str).str.strip()
    clientes["TARIFA"] = clientes["TARIFA"].astype(str).str.strip().str.upper()

    return clientes


def cargar_tarifa():
    archivo = buscar_excel_tarifa()

    if archivo is None:
        st.error("No hay Excel de tarifas")
        st.stop()

    df = pd.read_excel(archivo)
    df.columns = df.columns.str.strip().str.upper()

    df["PRECIO"] = df["PRECIO"].apply(limpiar_precio)
    df = df.dropna(subset=["PRECIO"])

    df["CLIENTE FINAL"] = df["PRECIO"] / 0.55
    df["ALTA DISTRIBUCION"] = df["PRECIO"] / 0.90
    df["HOSTELERIA"] = df["PRECIO"] / 0.80

    return df


# =========================
# ESTADO
# =========================

if "logueado" not in st.session_state:
    st.session_state.logueado = False

if "pedido" not in st.session_state:
    st.session_state.pedido = []


# =========================
# LOGIN
# =========================

if not st.session_state.logueado:
    st.markdown("### Acceso cliente")

    n_cliente = st.text_input("Nº cliente")
    password = st.text_input("Contraseña", type="password")

    if st.button("Entrar"):
        clientes = cargar_clientes()

        user = clientes[
            (clientes["N_CLIENTE"] == n_cliente) &
            (clientes["CONTRASEÑA"] == password)
        ]

        if user.empty:
            st.error("Datos incorrectos")
        else:
            user = user.iloc[0]
            st.session_state.logueado = True
            st.session_state.cliente = user["CLIENTE"]
            st.session_state.tarifa = user["TARIFA"]
            st.rerun()

    st.stop()


# =========================
# APP
# =========================

df = cargar_tarifa()

st.success(f"Cliente: {st.session_state.cliente}")

if st.button("Cerrar sesión"):
    st.session_state.logueado = False
    st.session_state.pedido = []
    st.rerun()


# =========================
# PEDIDO
# =========================

if st.session_state.pedido:
    total = sum(i["cajas"] for i in st.session_state.pedido)

    st.success(f"{len(st.session_state.pedido)} productos | {total} cajas")

    texto = crear_texto_pedido(st.session_state.cliente, st.session_state.pedido)
    url = "https://wa.me/?text=" + quote(texto)

    col1, col2 = st.columns(2)
    col1.link_button("Finalizar pedido", url)

    if col2.button("Vaciar"):
        st.session_state.pedido = []
        st.rerun()
else:
    st.info("Pedido vacío")


# =========================
# TARIFA
# =========================

if st.session_state.tarifa == "TODAS":
    tarifa = st.radio("Tarifa", ["1","2","3","4"], horizontal=True)
else:
    tarifa = st.session_state.tarifa
    st.info(f"Tarifa {tarifa}")

col_precio = TARIFAS[tarifa]


# =========================
# BUSCADOR + LISTA
# =========================

busqueda = st.text_input("Buscar")

if busqueda:
    resultados = df[df["DESCRIPCION"].str.contains(busqueda, case=False, na=False)]
else:
    resultados = df.head(40)

for i, fila in resultados.iterrows():

    descripcion = fila["DESCRIPCION"]
    formato = fila["FORMATO"]
    precio = fila[col_precio]

    st.markdown(
        f"<div class='producto'><b>{descripcion}</b> · {euros(precio)} € · {formato}</div>",
        unsafe_allow_html=True
    )

    col1, col2 = st.columns([1,1])

    with col1:
        cajas = st.number_input(
            "cajas",
            min_value=1,
            value=1,
            key=f"cajas_{i}",
            label_visibility="collapsed"
        )

    with col2:
        if st.button("Añadir", key=f"add_{i}"):
            st.session_state.pedido.append({
                "cajas": cajas,
                "descripcion": descripcion,
                "precio": precio,
                "formato": formato
            })
            st.rerun()

    st.markdown("---")
