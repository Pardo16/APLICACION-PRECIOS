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
    gap: 0.18rem;
}

hr {
    margin: 0.25rem 0;
}

.stButton button {
    padding: 0.18rem 0.35rem;
    font-size: 0.78rem;
    min-height: 1.8rem;
}

div[data-testid="stHorizontalBlock"] {
    gap: 0.25rem;
}

.product-line {
    font-size: 0.84rem;
    line-height: 1.12;
    margin-bottom: 0.05rem;
}

.qty-box {
    text-align: center;
    font-weight: 700;
    font-size: 0.85rem;
    padding-top: 0.25rem;
}

.added-msg {
    font-size: 0.75rem;
    color: #0a7a20;
    font-weight: 700;
    text-align: center;
    padding-top: 0.25rem;
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

if "nombre_cliente" not in st.session_state:
    st.session_state.nombre_cliente = ""


nombre_cliente = st.text_input("Cliente", value=st.session_state.nombre_cliente)
st.session_state.nombre_cliente = nombre_cliente.strip()

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
    total = sum(i["cajas"] for i in st.session_state.pedido)

    st.success(f"{len(st.session_state.pedido)} productos | {total} cajas")

    texto = crear_texto_pedido(st.session_state.nombre_cliente, st.session_state.pedido)
    url = "https://wa.me/?text=" + quote(texto)

    col1, col2 = st.columns(2)

    with col1:
        st.link_button("Finalizar pedido", url)

    with col2:
        if st.button("Vaciar"):
            st.session_state.pedido = []
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


busqueda = st.text_input("Buscar")

if busqueda:
    resultados = df[
        df["DESCRIPCION"].astype(str).str.contains(busqueda, case=False, na=False)
    ].reset_index(drop=True)

    if resultados.empty:
        st.warning("No se encontró ningún producto")
    else:
        for i, fila in resultados.iterrows():
            descripcion = str(fila["DESCRIPCION"])
            formato = str(fila["FORMATO"])
            precio = float(fila[col_precio])

            key_cajas = f"cajas_{i}_{tarifa}_{busqueda}"
            key_added = f"added_{i}_{tarifa}_{busqueda}"

            if key_cajas not in st.session_state:
                st.session_state[key_cajas] = 1

            if key_added not in st.session_state:
                st.session_state[key_added] = False

            st.markdown(
                f"""
                <div class="product-line">
                    <b>{descripcion}</b><br>
                    {euros(precio)} € · {formato}
                </div>
                """,
                unsafe_allow_html=True
            )

            col_menos, col_num, col_mas, col_add = st.columns([0.65, 0.55, 0.65, 1.45])

            with col_menos:
                if st.button("−", key=f"menos_{i}_{tarifa}_{busqueda}"):
                    if st.session_state[key_cajas] > 1:
                        st.session_state[key_cajas] -= 1
                    st.session_state[key_added] = False
                    st.rerun()

            with col_num:
                st.markdown(
                    f'<div class="qty-box">{st.session_state[key_cajas]}</div>',
                    unsafe_allow_html=True
                )

            with col_mas:
                if st.button("+", key=f"mas_{i}_{tarifa}_{busqueda}"):
                    st.session_state[key_cajas] += 1
                    st.session_state[key_added] = False
                    st.rerun()

            with col_add:
                if st.session_state[key_added]:
                    if st.button("Añadido", key=f"add_done_{i}_{tarifa}_{busqueda}"):
                        st.session_state[key_added] = False
                        st.rerun()
                else:
                    if st.button("Añadir", key=f"add_{i}_{tarifa}_{busqueda}"):
                        st.session_state.pedido.append({
                            "cajas": int(st.session_state[key_cajas]),
                            "descripcion": descripcion,
                            "precio": precio,
                            "formato": formato
                        })
                        st.session_state[key_added] = True
                        st.rerun()

            st.markdown("---")
