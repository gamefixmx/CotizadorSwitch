import streamlit as st
import pandas as pd
import urllib.parse
import base64

# 1. Configuración de la página
st.set_page_config(page_title="Gamefix - Cotizador Switch", page_icon="🎮", layout="wide")

st.title("🎮 Gamefix - Instalación de Juegos Nintendo Switch")
st.markdown("Elige tu memoria y selecciona los juegos que deseas instalar. ¡Nosotros hacemos el resto!")

# --- VARIABLES DE PRECIOS Y CAPACIDADES ---
PRECIO_SIN_MEMORIA = 1200
PRECIO_128GB = 1500
PRECIO_256GB = 2200
COSTO_JUEGO_EXTRA = 100

CAPACIDAD_128 = 119.0
CAPACIDAD_256 = 238.0
CAPACIDAD_PROPIA = 500.0
# ------------------------------------------------------------------------

# 2. Barra Lateral (Sidebar)
st.sidebar.image("logo.png", use_container_width=True)
st.sidebar.header("1. Opciones de Memoria")

opcion_memoria = st.sidebar.radio(
    "Selecciona el almacenamiento:",
    ["Sin memoria (Traigo mi propia SD)", "Comprar Memoria 128 GB", "Comprar Memoria 256 GB"]
)

if opcion_memoria == "Sin memoria (Traigo mi propia SD)":
    costo_base = PRECIO_SIN_MEMORIA
    capacidad_max = CAPACIDAD_PROPIA
elif opcion_memoria == "Comprar Memoria 128 GB":
    costo_base = PRECIO_128GB
    capacidad_max = CAPACIDAD_128
else:
    costo_base = PRECIO_256GB
    capacidad_max = CAPACIDAD_256

# 3. Cargar Base de Datos desde Google Sheets
@st.cache_data(ttl=60)
def cargar_juegos():
    SHEET_ID = '1NVQeuswZ0odOah7wrFMENsdx-uSYU7BhsVjnmFLQnpI'
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"
    try:
        df = pd.read_csv(url)
        df.dropna(subset=['Nombre'], inplace=True) 
        return df
    except Exception as e:
        st.error(f"Error al cargar la base de datos: {e}")
        return pd.DataFrame()

df_juegos = cargar_juegos()

# 4. Inyección CSS Global (Carga la imagen una sola vez para los 436 juegos)
@st.cache_data
def cargar_css_cartucho():
    try:
        with open("cartucho.png", "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
            return f"""
            <style>
            .cartucho-card {{
                background-image: url('data:image/png;base64,{b64}');
                background-size: contain;
                background-repeat: no-repeat;
                background-position: center;
                width: 100%;
                aspect-ratio: 351 / 508;
                position: relative;
                margin-bottom: 8px;
            }}
            .cartucho-texto {{
                position: absolute;
                top: 42%;
                left: 50%;
                transform: translate(-50%, -50%);
                width: 80%;
                text-align: center;
                font-family: 'Arial Black', Impact, sans-serif;
                font-size: 11px;
                color: #111111;
                line-height: 1.15;
                word-wrap: break-word;
            }}
            </style>
            """
    except:
        return ""

css_cartucho = cargar_css_cartucho()
if css_cartucho:
    st.markdown(css_cartucho, unsafe_allow_html=True)

# 5. Mostrar Catálogo de Juegos con Buscador Integrado
st.header("2. Catálogo de Juegos")
st.info(f"💡 **Nota:** Los primeros 10 juegos están incluidos en el costo base. A partir del 11avo juego, se sumarán ${COSTO_JUEGO_EXTRA} por cada uno.")

# Buscador para agilizar la experiencia con 400+ juegos
busqueda = st.text_input("🔍 Buscar juego por nombre:", "").strip().lower()

juegos_seleccionados = []
espacio_usado = 0.0

if not df_juegos.empty:
    # Filtrar según la búsqueda
    if busqueda:
        df_filtrado = df_juegos[df_juegos['Nombre'].astype(str).str.lower().str.contains(busqueda)]
    else:
        df_filtrado = df_juegos

    cols = st.columns(4)
    for index, row in df_filtrado.iterrows():
        with cols[index % 4]:
            with st.container(border=True):
                url_portada = row.get('URL_Portada', '')
                nombre_juego = str(row['Nombre'])
                
# Renderizar portada Tinfoil con el cartucho encima, o solo cartucho con texto
                if pd.notna(url_portada) and str(url_portada).strip() != "":
                    # EFECTO SÁNDWICH (Sin espacios a la izquierda para evitar que Streamlit lo vuelva texto)
                    html_portada = f"""<div style="position: relative; width: 100%; aspect-ratio: 351/508; margin: auto; margin-bottom: 8px;">
<img src="{str(url_portada).strip()}" style="position: absolute; left: 7.6%; top: 26.5%; width: 85%; height: 64%; object-fit: cover; border-radius: 4px; z-index: 1;">
<div class="cartucho-card" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 2; margin-bottom: 0;"></div>
</div>"""
                    st.markdown(html_portada, unsafe_allow_html=True)
                else:
                    # SIN URL: Muestra el cartucho genérico con el nombre escrito
                    html_vacio = f"""<div class="cartucho-card" style="margin-bottom: 8px;"><div class="cartucho-texto">{nombre_juego}</div></div>"""
                    st.markdown(html_vacio, unsafe_allow_html=True)
                
                st.markdown(f"**{nombre_juego}**")
                st.caption(f"📦 Peso: {row['Peso_GB']} GB")
                if str(row['Incluye_DLC']).strip().lower() == 'si':
                    st.caption("✨ Incluye DLC")
                
                if st.checkbox("Agregar al carrito", key=f"juego_{index}"):
                    juegos_seleccionados.append(nombre_juego)
                    espacio_usado += float(row['Peso_GB'])

# 6. Resumen de Espacio y Precios en Sidebar
st.sidebar.divider()
st.sidebar.header("2. Resumen de Espacio")

porcentaje_uso = min(espacio_usado / capacidad_max, 1.0) if capacidad_max > 0 else 0

if espacio_usado > capacidad_max and opcion_memoria != "Sin memoria (Traigo mi propia SD)":
    st.sidebar.error(f"⚠️ Espacio excedido. Quita algunos juegos.\nOcupas: {espacio_usado:.1f} GB de {capacidad_max} GB")
    st.sidebar.progress(1.0)
else:
    st.sidebar.success(f"**Espacio usado:** {espacio_usado:.1f} GB de {capacidad_max} GB")
    st.sidebar.progress(porcentaje_uso)

juegos_extra = max(0, len(juegos_seleccionados) - 10)
costo_total = costo_base + (juegos_extra * COSTO_JUEGO_EXTRA)

st.sidebar.divider()
st.sidebar.header("3. Cotización Final")
st.sidebar.write(f"🎮 **Juegos base (hasta 10):** {min(len(juegos_seleccionados), 10)}")
if juegos_extra > 0:
    st.sidebar.write(f"➕ **Juegos extra (+${COSTO_JUEGO_EXTRA}):** {juegos_extra}")

st.sidebar.subheader(f"💵 Total: ${costo_total} MXN")

# 7. Checkout por WhatsApp
st.sidebar.divider()
st.sidebar.markdown("### ¿Todo listo?")

if st.sidebar.button("📲 Enviar Pedido por WhatsApp", type="primary", use_container_width=True):
    if len(juegos_seleccionados) == 0:
        st.sidebar.warning("Por favor selecciona al menos un juego.")
    elif espacio_usado > capacidad_max and opcion_memoria != "Sin memoria (Traigo mi propia SD)":
        st.sidebar.error("No puedes enviar el pedido, excediste la memoria.")
    else:
        lista_texto = ", ".join(juegos_seleccionados)
        mensaje = f"¡Hola Gamefix! 👋 Quiero agendar una instalación de Nintendo Switch.\n\n"
        mensaje += f"📦 *Opción elegida:* {opcion_memoria}\n"
        mensaje += f"💾 *Espacio ocupado:* {espacio_usado:.1f} GB\n"
        mensaje += f"🎮 *Juegos seleccionados ({len(juegos_seleccionados)}):* {lista_texto}\n\n"
        mensaje += f"💵 *Costo Total Cotizado:* ${costo_total} MXN\n\n"
        mensaje += "¿Me proporcionas el link de pago de Mercado Pago o los datos de depósito?"
        
        numero_whatsapp = "529845208305"
        url_whatsapp = f"https://wa.me/{numero_whatsapp}?text={urllib.parse.quote(mensaje)}"
        
        st.sidebar.success("Haz clic en el enlace de abajo para abrir WhatsApp:")
        st.sidebar.markdown(f"[👉 **CONFIRMAR PEDIDO AQUÍ**]({url_whatsapp})")
