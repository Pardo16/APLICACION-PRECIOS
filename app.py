import base64
import json
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import requests
import streamlit as st


st.set_page_config(
    page_title="Precios Pescados Pardo",
    page_icon="🐟",
    layout="centered"
)

st.markdown("#### 🐟 Precios Pescados Pardo")

st.markdown("""
<style>
.block-container {
    padding-top: 0.6rem;
    padding-bottom: 0.8rem;
}

div[data-testid="stVerticalBlock"] {
    gap: 0.45rem;
}

hr {
    margin: 0.75rem 0;
}

.producto {
    font-size: 0.90rem;
    line-height: 1.35;
    margin-bottom: 0.75rem;
    padding-bottom: 0.35rem;
    display: block;
}

.producto b {
    font-weight: 800;
}

.stButton button {
    padding: 0.35rem 0.6rem;
    font-size: 0.90rem;
    min-height: 2.4rem;
}
</style>
""", unsafe_allow_html=True)


TARIFAS = {
    "1": "PRECIO",
    "2": "CLIENTE FINAL",
    "3": "ALTA DISTRIBUCION",
    "4": "HOSTELERIA",
}


def get_secret(nombre, defecto=""):
    try:
        return st.secrets.get(nombre, defecto)
    except Exception:
        return defecto


GITHUB_TOKEN = get_secret("GITHUB_TOKEN")
GITHUB_REPO = get_secret("GITHUB_REPO")
GITHUB_BRANCH = get_secret("GITHUB_BRANCH", "main")
FAVORITOS_PATH = get_secret("FAVORITOS_PATH", "favoritos.json")


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
    except Exception:
        return None


def euros(valor):
    return f"{float(valor):.2f}".replace(".", ",")


def cargar_clientes():
    archivo = buscar_excel_clientes()

    if archivo is None:
        st.error("No encuentro clientes.xlsx")
        st.stop()

    clientes = pd.read_excel(archivo)
    clientes.columns = clientes.columns.astype(str).str.strip().str.upper()

    columnas = ["N_CLIENTE", "CLIENTE", "CONTRASEÑA", "TARIFA"]
    faltan = [c for c in columnas if c not in clientes.columns]

    if faltan:
        st.error(f"Faltan columnas en clientes.xlsx: {faltan}")
        st.write("Columnas encontradas:", list(clientes.columns))
        st.stop()

    clientes["N_CLIENTE"] = clientes["N_CLIENTE"].astype(str).str.strip()
    clientes["CONTRASEÑA"] = clientes["CONTRASEÑA"].astype(str).str.strip()
    clientes["TARIFA"] = clientes["TARIFA"].astype(str).str.strip().str.upper()

    return clientes


def cargar_tarifa():
    archivo = buscar_excel_tarifa()

    if archivo is None:
        st.error("No encuentro ningún Excel de tarifa")
        st.stop()

    df = pd.read_excel(archivo)
    df.columns = df.columns.astype(str).str.strip().str.upper()

    columnas = ["CODIGO", "DESCRIPCION", "FORMATO", "PRECIO"]
    faltan = [c for c in columnas if c not in df.columns]

    if faltan:
        st.error(f"Faltan columnas en el Excel de tarifa: {faltan}")
        st.write("Columnas encontradas:", list(df.columns))
        st.stop()

    df["CODIGO"] = df["CODIGO"].astype(str).str.strip()
    df["PRECIO"] = df["PRECIO"].apply(limpiar_precio)
    df = df.dropna(subset=["PRECIO"])

    df["CLIENTE FINAL"] = df["PRECIO"] / 0.55
    df["ALTA DISTRIBUCION"] = df["PRECIO"] / 0.90
    df["HOSTELERIA"] = df["PRECIO"] / 0.80

    for col in ["PRECIO", "CLIENTE FINAL", "ALTA DISTRIBUCION", "HOSTELERIA"]:
        df[col] = df[col].round(2)

    return df


def github_headers():
    return {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }


def github_url():
    return f"https://api.github.com/repos/{GITHUB_REPO}/contents/{FAVORITOS_PATH}"


def cargar_favoritos():
    if GITHUB_TOKEN and GITHUB_REPO:
        try:
            r = requests.get(
                github_url(),
                headers=github_headers(),
                params={"ref": GITHUB_BRANCH},
                timeout=15
            )

            if r.status_code == 200:
                data = r.json()
                contenido = base64.b64decode(data["content"]).decode("utf-8")
                return json.loads(contenido or "{}"), data.get("sha")

        except Exception:
            pass

    archivo_local = Path("favoritos.json")

    if archivo_local.exists():
        try:
            return json.loads(archivo_local.read_text(encoding="utf-8") or "{}"), None
        except Exception:
            return {}, None

    return {}, None


def guardar_favoritos(favoritos, sha_actual=None):
    contenido_json = json.dumps(favoritos, ensure_ascii=False, indent=2)

    if GITHUB_TOKEN and GITHUB_REPO:
        try:
            payload = {
                "message": "Actualizar favoritos",
                "content": base64.b64encode(contenido_json.encode("utf-8")).decode("utf-8"),
                "branch": GITHUB_BRANCH,
            }

            if sha_actual:
                payload["sha"] = sha_actual

            r = requests.put(
                github_url(),
                headers=github_headers(),
                json=payload,
                timeout=15
            )

            return r.status_code in [200, 201]

        except Exception:
            return False

    try:
        Path("favoritos.json").write_text(contenido_json, encoding="utf-8")
        return True
    except Exception:
        return False


def registrar_favorito(n_cliente, codigo, cajas):
    favoritos, sha = cargar_favoritos()

    n_cliente = str(n_cliente)
    codigo = str(codigo)

    if n_cliente not in favoritos:
        favoritos[n_cliente] = {}

    if codigo not in favoritos[n_cliente]:
        favoritos[n_cliente][codigo] = 0

    favoritos[n_cliente][codigo] += int(cajas)

    guardar_favoritos(favoritos, sha)


def productos_favoritos(df, n_cliente):
    favoritos, _ = cargar_favoritos()

    datos_cliente = favoritos.get(str(n_cliente), {})

    if not datos_cliente:
        return pd.DataFrame()

    codigos_ordenados = sorted(
        datos_cliente.keys(),
        key=lambda c: datos_cliente[c],
        reverse=True
    )

    df_fav = df[df["CODIGO"].astype(str).isin(codigos_ordenados)].copy()

    if df_fav.empty:
        return df_fav

    df_fav["ORDEN_FAVORITO"] = df_fav["CODIGO"].astype(str).map(
        {codigo: i for i, codigo in enumerate(codigos_ordenados)}
    )

    return df_fav.sort_values("ORDEN_FAVORITO").drop(columns=["ORDEN_FAVORITO"])


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


def agregar_al_pedido(item_nuevo):
    for item in st.session_state.pedido:
        mismo_codigo = str(item.get("codigo")) == str(item_nuevo.get("codigo"))
        misma_tarifa = str(item.get("tarifa")) == str(item_nuevo.get("tarifa"))

        if mismo_codigo and misma_tarifa:
            item["cajas"] += item_nuevo["cajas"]
            return

    st.session_state.pedido.append(item_nuevo)


if "logueado" not in st.session_state:
    st.session_state.logueado = False

if "pedido" not in st.session_state:
    st.session_state.pedido = []

if "cliente" not in st.session_state:
    st.session_state.cliente = ""

if "n_cliente" not in st.session_state:
    st.session_state.n_cliente = ""

if "tarifa_cliente" not in st.session_state:
    st.session_state.tarifa_cliente = ""

if "ultimo_anadido" not in st.session_state:
    st.session_state.ultimo_anadido = ""


if not st.session_state.logueado:
    st.markdown("### Acceso cliente")

    n_cliente = st.text_input("Nº cliente", value=st.session_state.get("n_cliente_login", ""))
    password = st.text_input("Contraseña", type="password")

    if st.button("Entrar"):
        clientes = cargar_clientes()

        usuario = clientes[
            (clientes["N_CLIENTE"] == str(n_cliente).strip()) &
            (clientes["CONTRASEÑA"] == str(password).strip())
        ]

        if usuario.empty:
            st.error("Nº cliente o contraseña incorrectos.")
        else:
            usuario = usuario.iloc[0]

            st.session_state.logueado = True
            st.session_state.n_cliente = str(usuario["N_CLIENTE"])
            st.session_state.n_cliente_login = str(usuario["N_CLIENTE"])
            st.session_state.cliente = str(usuario["CLIENTE"])
            st.session_state.tarifa_cliente = str(usuario["TARIFA"]).upper()
            st.session_state.pedido = []

            st.rerun()

    st.stop()


df = cargar_tarifa()

st.success(f"Cliente: {st.session_state.cliente}")

if st.button("Cerrar sesión"):
    st.session_state.logueado = False
    st.session_state.pedido = []
    st.session_state.cliente = ""
    st.session_state.n_cliente = ""
    st.session_state.tarifa_cliente = ""
    st.session_state.ultimo_anadido = ""
    st.rerun()


st.markdown("### 🧾 Pedido")

if st.session_state.pedido:
    total = sum(item["cajas"] for item in st.session_state.pedido)
    st.success(f"{len(st.session_state.pedido)} productos | {total} cajas")

    with st.expander("Ver / modificar pedido", expanded=False):
        for idx, item in enumerate(st.session_state.pedido):
            st.markdown(
                f"**{item['descripcion']}**  \n"
                f"{euros(item['precio'])} € · {item['formato']}"
            )

            col1, col2, col3 = st.columns([1, 1, 1])

            with col1:
                nueva_cantidad = st.number_input(
                    "Cajas",
                    min_value=1,
                    value=int(item["cajas"]),
                    step=1,
                    key=f"edit_cajas_{idx}",
                    label_visibility="collapsed"
                )
                st.session_state.pedido[idx]["cajas"] = int(nueva_cantidad)

            with col2:
                if st.button("Quitar", key=f"quitar_{idx}"):
                    st.session_state.pedido.pop(idx)
                    st.rerun()

            with col3:
                subtotal = int(st.session_state.pedido[idx]["cajas"]) * float(item["precio"])
                st.write(f"{euros(subtotal)} €")

            st.markdown("---")

    texto = crear_texto_pedido(st.session_state.cliente, st.session_state.pedido)
    url = "https://wa.me/?text=" + quote(texto)

    col1, col2 = st.columns(2)

    with col1:
        st.link_button("Finalizar pedido", url)

    with col2:
        if st.button("Vaciar pedido"):
            st.session_state.pedido = []
            st.rerun()
else:
    st.info("Pedido vacío")


tarifa_cliente = st.session_state.tarifa_cliente

if tarifa_cliente == "TODAS":
    tarifa_visible = st.radio(
        "Tarifa",
        ["1", "2", "3", "4"],
        horizontal=True,
        format_func=lambda x: f"Tarifa {x}"
    )
else:
    tarifa_visible = tarifa_cliente
    st.info(f"Tarifa {tarifa_visible}")

if tarifa_visible not in TARIFAS:
    st.error("La tarifa asignada no es válida. Usa 1, 2, 3, 4 o TODAS en clientes.xlsx.")
    st.stop()

col_precio = TARIFAS[tarifa_visible]


busqueda = st.text_input("Buscar", placeholder="Ej: anilla, atún, calamar...")

if busqueda:
    resultados = df[
        df["DESCRIPCION"].astype(str).str.contains(busqueda, case=False, na=False)
    ].reset_index(drop=True)
else:
    favoritos_df = productos_favoritos(df, st.session_state.n_cliente)

    if not favoritos_df.empty:
        st.caption("Productos habituales")
        resultados = favoritos_df.head(30).reset_index(drop=True)
    else:
        st.caption("Mostrando primeros 30 productos. Usa el buscador para filtrar.")
        resultados = df.head(30).reset_index(drop=True)


if resultados.empty:
    st.warning("No se encontró ningún producto")
else:
    for i, fila in resultados.iterrows():
        codigo = str(fila["CODIGO"])
        descripcion = str(fila["DESCRIPCION"])
        formato = str(fila["FORMATO"])
        precio = float(fila[col_precio])

        key = f"cajas_{i}_{codigo}_{tarifa_visible}_{busqueda}"

        if key not in st.session_state:
            st.session_state[key] = 1

        st.markdown(
            f"""
            <div class="producto">
                <b>{descripcion}</b> · {euros(precio)} € · {formato}
            </div>
            """,
            unsafe_allow_html=True
        )

        col1, col2 = st.columns([1, 1])

        with col1:
            cajas = st.number_input(
                "Cajas",
                min_value=1,
                value=st.session_state[key],
                step=1,
                key=key,
                label_visibility="collapsed"
            )

        with col2:
            boton_id = f"{codigo}_{tarifa_visible}"

            texto_boton = "✅ Añadido" if st.session_state.ultimo_anadido == boton_id else "Añadir"

            if st.button(texto_boton, key=f"add_{i}_{codigo}_{tarifa_visible}_{busqueda}"):
                agregar_al_pedido({
                    "cajas": int(cajas),
                    "codigo": codigo,
                    "descripcion": descripcion,
                    "precio": precio,
                    "formato": formato,
                    "tarifa": tarifa_visible,
                })

                registrar_favorito(
                    st.session_state.n_cliente,
                    codigo,
                    int(cajas)
                )

                st.session_state.ultimo_anadido = boton_id
                st.rerun()

        st.markdown("---")
