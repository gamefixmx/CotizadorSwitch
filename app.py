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

# 3. Cargar Base de Datos
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

# --- NUEVO: Cargar el cartucho una sola vez súper rápido ---
@st.cache_data
def obtener_cartucho_base64():
    try:
        with open("cartucho.png", "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except:
        return ""

cartucho_b64 = obtener_cartucho_base64()
# -----------------------------------------------------------

# 4. Mostrar Catálogo de Juegos
st.header("2. Catálogo de Juegos")
st.info(f"💡 **Nota:** Los primeros 10 juegos están incluidos en el costo base. A partir del 11avo juego, se sumarán ${COSTO_JUEGO_EXTRA} por cada uno.")

juegos_seleccionados = []
espacio_usado = 0.0

if not df_juegos.empty:
    cols = st.columns(4)
    for index, row in df_juegos.iterrows():
        with cols[index % 4]:
            with st.container(border=True):
                url_portada = row.get('URL_Portada', '')
                nombre_juego = row['Nombre']
                
                # Mostrar portada si existe, si no, usar HTML ultra rápido para el cartucho
                if pd.notna(url_portada) and str(url_portada).strip() != "":
                    try:
                        st.image(str(url_portada).strip(), use_container_width=True)
                    except:
                        # Si el link falla, mostramos el cartucho HTML
                        if cartucho_b64:
                            st.markdown(f"""
                            <div style="position: relative; width: 100%; margin: auto;">
                                <img src="data:image/png;base64,{cartucho_b64}" style="width: 100%; border-radius: 8px;">
                                <div style="position: absolute; top: 43%; left: 50%; transform: translate(-50%, -50%); width: 85%; text-align: center; font-family: 'Arial Black', Impact, sans-serif; font-size: 13px; color: #111; line-height: 1.1; word-wrap: break-word;">
                                    {nombre_juego}
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                else:
                    if cartucho_b64:
                        st.markdown(f"""
                        <div style="position: relative; width: 100%; margin: auto;">
                            <img src="data:image/png;base64,{cartucho_b64}" style="width: 100%; border-radius: 8px;">
                            <div style="position: absolute; top: 43%; left: 50%; transform: translate(-50%, -50%); width: 85%; text-align: center; font-family: 'Arial Black', Impact, sans-serif; font-size: 13px; color: #111; line-height: 1.1; word-wrap: break-word;">
                                {nombre_juego}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                
                st.markdown(f"**{nombre_juego}**")
                st.caption(f"📦 Peso: {row['Peso_GB']} GB")
                if str(row['Incluye_DLC']).strip().lower() == 'si':
                    st.caption("✨ Incluye DLC")
                
                if st.checkbox("Agregar al carrito", key=f"juego_{index}"):
                    juegos_seleccionados.append(nombre_juego)
                    espacio_usado += float(row['Peso_GB'])

# 5. Resumen Sidebar
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

# 6. Checkout WhatsApp
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
