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

.producto {
    font-size: 0.88rem;
    line-height: 1.15;
    margin-bottom: 0.25rem;
}

.acciones {
    display: flex;
    flex-direction: row;
    align-items: center;
    gap: 8px;
    margin-top: 0.2rem;
    margin-bottom: 0.45rem;
}

.btn-mini {
    display: inline-block;
    padding: 6px 12px;
    border: 1px solid #555;
    border-radius: 8px;
    text-decoration: none !important;
    color: inherit !important;
    font-weight: 700;
    min-width: 28px;
    text-align: center;
}

.cantidad {
    font-weight: 800;
    font-size: 1rem;
    min-width: 24px;
    text-align: center;
}

.btn-add {
    display: inline-block;
    padding: 6px 16px;
    border: 1px solid #555;
    border-radius: 8px;
    text-decoration: none !important;
    color: inherit !important;
    font-weight: 700;
}

hr {
    margin: 0.35rem 0;
}

/* 🔥 INPUT VERDE */
div[data-baseweb="input"] input {
    border: 2px solid #28a745 !important;
    box-shadow: none !important;
}

div[data-baseweb="input"] input:focus {
    border: 2px solid #28a745 !important;
    box-shadow: 0 0 0 1px #28a745 !important;
}

div[data-baseweb="input"] {
    border-radius: 8px;
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

if "cantidades" not in st.session_state:
    st.session_state.cantidades = {}

if "ultimo_anadido" not in st.session_state:
    st.session_state.ultimo_anadido = ""


nombre_cliente = st.text_input(
    "Cliente",
    value=st.session_state.nombre_cliente,
    placeholder="Nombre del cliente"
)

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
df = df.dropna(subset=["PRECIO"]).reset_index(drop=True)

df["ITEM_ID"] = df.index.astype(str)

df["CLIENTE FINAL"] = df["PRECIO"] / 0.55
df["ALTA DISTRIBUCION"] = df["PRECIO"] / 0.90
df["HOSTELERIA"] = df["PRECIO"] / 0.80

for col in ["PRECIO", "CLIENTE FINAL", "ALTA DISTRIBUCION", "HOSTELERIA"]:
    df[col] = df[col].round(2)


# Acciones botones HTML
params = st.query_params

accion = params.get("accion", None)
item_id = params.get("item", None)
tarifa_param = params.get("tarifa", None)

if accion and item_id is not None:
    key_cantidad = f"cantidad_{item_id}"

    if key_cantidad not in st.session_state.cantidades:
        st.session_state.cantidades[key_cantidad] = 1

    if accion == "menos":
        if st.session_state.cantidades[key_cantidad] > 1:
            st.session_state.cantidades[key_cantidad] -= 1

    elif accion == "mas":
        st.session_state.cantidades[key_cantidad] += 1

    elif accion == "add":
        fila_add = df[df["ITEM_ID"] == str(item_id)]

        if not fila_add.empty:
            fila_add = fila_add.iloc[0]

            columna_precio_add = {
                "Coste": "PRECIO",
                "Cliente final": "CLIENTE FINAL",
                "Alta distribución": "ALTA DISTRIBUCION",
                "Hostelería": "HOSTELERIA",
            }.get(tarifa_param, "PRECIO")

            st.session_state.pedido.append({
                "cajas": int(st.session_state.cantidades[key_cantidad]),
                "codigo": str(fila_add["CODIGO"]),
                "descripcion": str(fila_add["DESCRIPCION"]),
                "precio": float(fila_add[columna_precio_add]),
                "formato": str(fila_add["FORMATO"]),
                "tarifa": tarifa_param or "Coste",
            })

            st.session_state.ultimo_anadido = str(item_id)

    st.query_params.clear()
    st.rerun()


if st.session_state.pedido:
    total = sum(item["cajas"] for item in st.session_state.pedido)
    st.success(f"{len(st.session_state.pedido)} productos | {total} cajas")

    texto = crear_texto_pedido(st.session_state.nombre_cliente, st.session_state.pedido)
    url = "https://wa.me/?text=" + quote(texto)

    col1, col2 = st.columns(2)

    with col1:
        st.link_button("Finalizar pedido", url)

    with col2:
        if st.button("Vaciar"):
            st.session_state.pedido = []
            st.session_state.ultimo_anadido = ""
            st.session_state.cantidades = {}
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
        for _, fila in resultados.iterrows():
            item_id = str(fila["ITEM_ID"])
            descripcion = str(fila["DESCRIPCION"])
            formato = str(fila["FORMATO"])
            precio = float(fila[col_precio])

            key_cantidad = f"cantidad_{item_id}"

            if key_cantidad not in st.session_state.cantidades:
                st.session_state.cantidades[key_cantidad] = 1

            cantidad = st.session_state.cantidades[key_cantidad]

            texto_add = "Añadido" if st.session_state.ultimo_anadido == item_id else "Añadir"

            url_menos = f"?accion=menos&item={quote(item_id)}&tarifa={quote(tarifa)}"
            url_mas = f"?accion=mas&item={quote(item_id)}&tarifa={quote(tarifa)}"
            url_add = f"?accion=add&item={quote(item_id)}&tarifa={quote(tarifa)}"

            st.markdown(
                f"""
                <div class="producto">
                    <b>{descripcion}</b> · {euros(precio)} € · {formato}
                </div>

                <div class="acciones">
                    <a class="btn-mini" href="{url_menos}">−</a>
                    <span class="cantidad">{cantidad}</span>
                    <a class="btn-mini" href="{url_mas}">+</a>
                    <a class="btn-add" href="{url_add}">{texto_add}</a>
                </div>
                """,
                unsafe_allow_html=True
            )

            st.markdown("---")
