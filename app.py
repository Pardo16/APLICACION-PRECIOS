import streamlit as st
import pandas as pd
from pathlib import Path
from urllib.parse import quote

st.set_page_config(page_title="Precios Pescados Pardo", page_icon="🐟", layout="centered")

st.markdown("#### 🐟 Precios Pescados Pardo")

st.markdown("""
<style>
.block-container {padding-top: 0.5rem; padding-bottom: 0.5rem;}
div[data-testid="stVerticalBlock"] {gap: 0.15rem;}
hr {margin: 0.3rem 0;}

.producto {
    font-size: 0.85rem;
    line-height: 1.1;
}

.stButton button {
    width: 100%;
    padding: 0.3rem;
    font-size: 0.8rem;
}

.qty {
    text-align:center;
    font-weight:700;
    font-size:1rem;
    padding-top:0.35rem;
}
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


def euros(v):
    return f"{float(v):.2f}".replace(".", ",")


def crear_texto(nombre, pedido):
    lineas = ["PEDIDO", f"Cliente: {nombre}", ""]
    total = 0
    for p in pedido:
        total += p["cajas"]
        lineas.append(f"- {p['cajas']} cajas | {p['descripcion']} | {euros(p['precio'])} € | {p['formato']}")
    lineas.append("")
    lineas.append(f"Total cajas: {total}")
    return "\n".join(lineas)


if "pedido" not in st.session_state:
    st.session_state.pedido = []

nombre = st.text_input("Cliente")
if not nombre:
    st.warning("Escribe el cliente")
    st.stop()


archivo = buscar_excel()
if archivo is None:
    st.error("No hay Excel")
    st.stop()

df = pd.read_excel(archivo)
df.columns = df.columns.str.strip().str.upper()

df["PRECIO"] = df["PRECIO"].apply(limpiar_precio)
df = df.dropna(subset=["PRECIO"])

df["CLIENTE FINAL"] = df["PRECIO"] / 0.55
df["ALTA DISTRIBUCION"] = df["PRECIO"] / 0.90
df["HOSTELERIA"] = df["PRECIO"] / 0.80

tarifa = st.radio("Tarifa", ["Coste", "Cliente final", "Alta distribución", "Hostelería"], horizontal=True)

col_precio = {
    "Coste": "PRECIO",
    "Cliente final": "CLIENTE FINAL",
    "Alta distribución": "ALTA DISTRIBUCION",
    "Hostelería": "HOSTELERIA",
}[tarifa]


# Pedido arriba
if st.session_state.pedido:
    total = sum(i["cajas"] for i in st.session_state.pedido)
    st.success(f"{len(st.session_state.pedido)} productos | {total} cajas")

    texto = crear_texto(nombre, st.session_state.pedido)
    url = "https://wa.me/?text=" + quote(texto)

    col1, col2 = st.columns(2)
    col1.link_button("Finalizar pedido", url)

    if col2.button("Vaciar"):
        st.session_state.pedido = []
        st.rerun()


busqueda = st.text_input("Buscar")

if busqueda:
    resultados = df[df["DESCRIPCION"].str.contains(busqueda, case=False, na=False)].reset_index(drop=True)

    for i, fila in resultados.iterrows():
        desc = fila["DESCRIPCION"]
        formato = fila["FORMATO"]
        precio = fila[col_precio]

        key = f"q_{i}"

        if key not in st.session_state:
            st.session_state[key] = 1

        # 🔹 LINEA 1
        st.markdown(
            f"<div class='producto'><b>{desc}</b><br>{euros(precio)} € · {formato}</div>",
            unsafe_allow_html=True
        )

        # 🔹 LINEA 2 (SOLO 2 COLUMNAS → NO SE ROMPE)
        col_izq, col_der = st.columns([2, 2])

        with col_izq:
            sub1, sub2, sub3 = st.columns([1,1,1])

            with sub1:
                if st.button("−", key=f"m_{i}"):
                    if st.session_state[key] > 1:
                        st.session_state[key] -= 1
                    st.rerun()

            with sub2:
                st.markdown(f"<div class='qty'>{st.session_state[key]}</div>", unsafe_allow_html=True)

            with sub3:
                if st.button("+", key=f"p_{i}"):
                    st.session_state[key] += 1
                    st.rerun()

        with col_der:
            if st.button("Añadir", key=f"a_{i}"):
                st.session_state.pedido.append({
                    "cajas": st.session_state[key],
                    "descripcion": desc,
                    "precio": precio,
                    "formato": formato
                })
                st.success("✔ Añadido")
                st.rerun()

        st.markdown("---")
