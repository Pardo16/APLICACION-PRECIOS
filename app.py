import streamlit as st
import pandas as pd
from pathlib import Path
from urllib.parse import quote

st.set_page_config(page_title="Precios Pescados Pardo", page_icon="🐟", layout="centered")

st.markdown("#### 🐟 Precios Pescados Pardo")

st.markdown("""
<style>
.block-container {
    padding-top: 0.5rem;
    padding-bottom: 0.5rem;
}

div[data-testid="stVerticalBlock"] {
    gap: 0.12rem;
}

hr {
    margin: 0.28rem 0;
}

.producto {
    font-size: 0.85rem;
    line-height: 1.15;
    margin-bottom: 0.15rem;
}

/* FORZAR COLUMNAS EN MÓVIL */
div[data-testid="stHorizontalBlock"] {
    display: flex !important;
    flex-direction: row !important;
    flex-wrap: nowrap !important;
    gap: 0.25rem !important;
    align-items: center !important;
}

div[data-testid="column"] {
    flex: 1 1 0 !important;
    min-width: 0 !important;
    width: auto !important;
}

.stButton button {
    width: 100%;
    padding: 0.22rem 0.25rem;
    font-size: 0.78rem;
    min-height: 2rem;
}

.qty {
    text-align: center;
    font-weight: 700;
    font-size: 0.95rem;
    padding-top: 0.35rem;
}
</style>
""", unsafe_allow_html=True)


def buscar_excel():
    archivos = list(Path(".").glob("*.xlsx")) + list(Path(".").glob("*.xls"))
    return archivos[0] if archivos else None


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


def crear_texto_pedido(nombre, pedido):
    lineas = ["PEDIDO", f"Cliente: {nombre}", ""]
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

if "nombre_cliente" not in st.session_state:
    st.session_state.nombre_cliente = ""

if "ultimo_anadido" not in st.session_state:
    st.session_state.ultimo_anadido = ""


nombre = st.text_input(
    "Cliente",
    value=st.session_state.nombre_cliente,
    placeholder="Nombre del cliente"
)

st.session_state.nombre_cliente = nombre.strip()

if not st.session_state.nombre_cliente:
    st.warning("Escribe el nombre del cliente")
    st.stop()


archivo = buscar_excel()

if archivo is None:
    st.error("No hay Excel en el repositorio")
    st.stop()


df = pd.read_excel(archivo)
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


if st.session_state.pedido:
    total = sum(item["cajas"] for item in st.session_state.pedido)
    st.success(f"{len(st.session_state.pedido)} productos | {total} cajas")

    texto = crear_texto_pedido(st.session_state.nombre_cliente, st.session_state.pedido)
    url = "https://wa.me/?text=" + quote(texto)

    col1, col2 = st.columns([1, 1])

    with col1:
        st.link_button("Finalizar", url)

    with col2:
        if st.button("Vaciar"):
            st.session_state.pedido = []
            st.session_state.ultimo_anadido = ""
            st.rerun()
else:
    st.info(f"Pedido vacío | {st.session_state.nombre_cliente}")


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


busqueda = st.text_input("Buscar", placeholder="Ej: anilla, atún, calamar...")

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
            precio = float(fila[col_precio])

            key_cajas = f"cajas_{i}_{codigo}_{tarifa}_{busqueda}"
            key_add = f"add_{i}_{codigo}_{tarifa}_{busqueda}"

            if key_cajas not in st.session_state:
                st.session_state[key_cajas] = 1

            st.markdown(
                f"""
                <div class="producto">
                    <b>{descripcion}</b><br>
                    {euros(precio)} € · {formato}
                </div>
                """,
                unsafe_allow_html=True
            )

            col_menos, col_cantidad, col_mas, col_add = st.columns([0.8, 0.7, 0.8, 2.2])

            with col_menos:
                if st.button("−", key=f"menos_{i}_{codigo}_{tarifa}_{busqueda}"):
                    if st.session_state[key_cajas] > 1:
                        st.session_state[key_cajas] -= 1
                    st.rerun()

            with col_cantidad:
                st.markdown(
                    f'<div class="qty">{st.session_state[key_cajas]}</div>',
                    unsafe_allow_html=True
                )

            with col_mas:
                if st.button("+", key=f"mas_{i}_{codigo}_{tarifa}_{busqueda}"):
                    st.session_state[key_cajas] += 1
                    st.rerun()

            with col_add:
                texto_boton = "Añadido" if st.session_state.ultimo_anadido == key_add else "Añadir"

                if st.button(texto_boton, key=key_add):
                    st.session_state.pedido.append({
                        "cajas": int(st.session_state[key_cajas]),
                        "codigo": codigo,
                        "descripcion": descripcion,
                        "precio": precio,
                        "formato": formato,
                        "tarifa": tarifa,
                    })
                    st.session_state.ultimo_anadido = key_add
                    st.rerun()

            st.markdown("---")
