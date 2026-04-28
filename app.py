import streamlit as st
import pandas as pd
from pathlib import Path
from urllib.parse import quote

st.set_page_config(
    page_title="Precios Pescados Pardo",
    page_icon="🐟",
    layout="centered"
)

# Título pequeño
st.markdown("### 🐟 Precios Pescados Pardo")


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


def crear_texto_pedido(nombre_cliente, pedido):
    lineas = [
        "PEDIDO",
        f"Cliente: {nombre_cliente}",
        ""
    ]

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


# Nombre antes de trabajar
nombre_cliente = st.text_input(
    "Nombre del cliente",
    value=st.session_state.nombre_cliente,
    placeholder="Escribe el nombre del cliente"
)

st.session_state.nombre_cliente = nombre_cliente.strip()

if not st.session_state.nombre_cliente:
    st.warning("Escribe el nombre del cliente para empezar el pedido.")
    st.stop()


archivo_excel = buscar_excel()

if archivo_excel is None:
    st.error("No hay ningún Excel en el repositorio.")
else:
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

        # Pedido arriba
        st.markdown("#### 🧾 Pedido")

        if st.session_state.pedido:
            total_cajas = sum(item["cajas"] for item in st.session_state.pedido)
            st.success(
                f"Cliente: {st.session_state.nombre_cliente} | "
                f"Productos: {len(st.session_state.pedido)} | "
                f"Cajas: {total_cajas}"
            )

            texto_pedido = crear_texto_pedido(
                st.session_state.nombre_cliente,
                st.session_state.pedido
            )

            with st.expander("Ver pedido"):
                st.text(texto_pedido)

            whatsapp_url = "https://wa.me/?text=" + quote(texto_pedido)

            st.link_button("✅ Finalizar pedido por WhatsApp", whatsapp_url)

            if st.button("Vaciar pedido"):
                st.session_state.pedido = []
                st.rerun()
        else:
            st.info(f"Pedido vacío | Cliente: {st.session_state.nombre_cliente}")

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

        busqueda = st.text_input("Buscar producto", placeholder="Ej: anilla, atún, calamar...")

        if busqueda:
            resultados = df[
                df["DESCRIPCION"].astype(str).str.contains(busqueda, case=False, na=False)
            ].reset_index(drop=True)

            if resultados.empty:
                st.warning("No se encontró ningún producto")
            else:
                resultados_vista = resultados.copy()
                resultados_vista["PRECIO"] = resultados_vista[columna_precio]

                st.dataframe(
                    resultados_vista[["DESCRIPCION", "PRECIO", "FORMATO"]],
                    use_container_width=True,
                    hide_index=True
                )

                producto_elegido = st.selectbox(
                    "Producto para añadir",
                    resultados.index,
                    format_func=lambda i: (
                        f"{resultados.loc[i, 'DESCRIPCION']} | "
                        f"{euros(resultados.loc[i, columna_precio])} € | "
                        f"{resultados.loc[i, 'FORMATO']}"
                    )
                )

                col1, col2 = st.columns([1, 2])

                with col1:
                    cajas = st.number_input(
                        "Cajas",
                        min_value=1,
                        value=1,
                        step=1
                    )

                with col2:
                    st.write("")
                    if st.button("➕ Añadir al pedido"):
                        fila = resultados.loc[producto_elegido]

                        st.session_state.pedido.append({
                            "cajas": int(cajas),
                            "codigo": str(fila["CODIGO"]),
                            "descripcion": str(fila["DESCRIPCION"]),
                            "precio": float(fila[columna_precio]),
                            "formato": str(fila["FORMATO"]),
                            "tarifa": tarifa,
                        })

                        st.rerun()
