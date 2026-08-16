import streamlit as st
import pandas as pd
import urllib.parse

# 1. Configuración de la página
st.set_page_config(page_title="Gamefix - Cotizador Switch", page_icon="🎮", layout="wide")

st.title("🎮 Gamefix - Instalación de Juegos Nintendo Switch")
st.markdown("Elige tu memoria y selecciona los juegos que deseas instalar. ¡Nosotros hacemos el resto!")

# --- VARIABLES DE PRECIOS Y CAPACIDADES (Puedes editar esto después) ---
PRECIO_SIN_MEMORIA = 1200   # Costo solo por el servicio de instalación
PRECIO_128GB = 1500         # Costo servicio + memoria 128GB
PRECIO_256GB = 2200        # Costo servicio + memoria 256GB
COSTO_JUEGO_EXTRA = 100     # Costo por cada juego extra a partir del número 11

CAPACIDAD_128 = 119.0      # Capacidad real en GB
CAPACIDAD_256 = 238.0      # Capacidad real en GB
CAPACIDAD_PROPIA = 500.0   # Un límite alto si traen su propia memoria
# ------------------------------------------------------------------------

# 2. Barra Lateral (Sidebar) para Opciones de Memoria y Resumen
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/5260/5260498.png", width=100) # Logo genérico temporal
st.sidebar.header("1. Opciones de Memoria")

opcion_memoria = st.sidebar.radio(
    "Selecciona el almacenamiento:",
    ["Sin memoria (Traigo mi propia SD)", "Comprar Memoria 128 GB", "Comprar Memoria 256 GB"]
)

# Lógica de costos y capacidades según la memoria elegida
if opcion_memoria == "Sin memoria (Traigo mi propia SD)":
    costo_base = PRECIO_SIN_MEMORIA
    capacidad_max = CAPACIDAD_PROPIA
elif opcion_memoria == "Comprar Memoria 128 GB":
    costo_base = PRECIO_128GB
    capacidad_max = CAPACIDAD_128
else:
    costo_base = PRECIO_256GB
    capacidad_max = CAPACIDAD_256

# 3. Cargar la base de datos de juegos (El archivo CSV)
@st.cache_data
def cargar_juegos():
    try:
        # Lee el archivo CSV separando por comas
        df = pd.read_csv("juegos.csv")
        return df
    except FileNotFoundError:
        st.error("No se encontró el archivo juegos.csv")
        return pd.DataFrame()

df_juegos = cargar_juegos()

# 4. Mostrar Catálogo de Juegos
st.header("2. Catálogo de Juegos")
st.info("💡 **Nota:** Los primeros 10 juegos están incluidos en el costo base. A partir del 11avo juego, se sumarán $" + str(COSTO_JUEGO_EXTRA) + " por cada uno.")

juegos_seleccionados = []
espacio_usado = 0.0

# Usamos columnas para mostrar los juegos como una tienda (ej. 4 columnas)
if not df_juegos.empty:
    cols = st.columns(4)
    for index, row in df_juegos.iterrows():
        # Distribuir en las columnas
        with cols[index % 4]:
            with st.container(border=True):
                # Mostrar imagen si hay URL, si no, un texto
                if pd.notna(row['URL_Portada']) and row['URL_Portada'].strip() != "":
                    try:
                        st.image(row['URL_Portada'], use_container_width=True)
                    except:
                        st.write("🖼️ *(Falta portada)*")
                else:
                    st.write("🖼️ *(Falta portada)*")
                
                # Información del juego
                st.markdown(f"**{row['Nombre']}**")
                st.caption(f"📦 Peso: {row['Peso_GB']} GB")
                if str(row['Incluye_DLC']).strip().lower() == 'si':
                    st.caption("✨ Incluye DLC")
                
                # Checkbox para seleccionar
                if st.checkbox("Agregar al carrito", key=f"juego_{index}"):
                    juegos_seleccionados.append(row['Nombre'])
                    espacio_usado += float(row['Peso_GB'])

# 5. Lógica de Precios y Barra de Progreso en la Sidebar
st.sidebar.divider()
st.sidebar.header("2. Resumen de Espacio")

# Calcular porcentaje para la barra
porcentaje_uso = min(espacio_usado / capacidad_max, 1.0) if capacidad_max > 0 else 0

# Alerta si excede capacidad (solo si no es memoria propia)
if espacio_usado > capacidad_max and opcion_memoria != "Sin memoria (Traigo mi propia SD)":
    st.sidebar.error(f"⚠️ Espacio excedido. Quita algunos juegos.\nOcupas: {espacio_usado:.1f} GB de {capacidad_max} GB")
    st.sidebar.progress(1.0)
else:
    st.sidebar.success(f"**Espacio usado:** {espacio_usado:.1f} GB de {capacidad_max} GB")
    st.sidebar.progress(porcentaje_uso)

# Cálculo de Precio
juegos_extra = max(0, len(juegos_seleccionados) - 10)
costo_total = costo_base + (juegos_extra * COSTO_JUEGO_EXTRA)

st.sidebar.divider()
st.sidebar.header("3. Cotización Final")
st.sidebar.write(f"🎮 **Juegos base (hasta 10):** {min(len(juegos_seleccionados), 10)}")
if juegos_extra > 0:
    st.sidebar.write(f"➕ **Juegos extra (+${COSTO_JUEGO_EXTRA}):** {juegos_extra}")

st.sidebar.subheader(f"💵 Total: ${costo_total} MXN")

# 6. Botón de Checkout por WhatsApp
st.sidebar.divider()
st.sidebar.markdown("### ¿Todo listo?")

if st.sidebar.button("📲 Enviar Pedido por WhatsApp", type="primary", use_container_width=True):
    if len(juegos_seleccionados) == 0:
        st.sidebar.warning("Por favor selecciona al menos un juego.")
    elif espacio_usado > capacidad_max and opcion_memoria != "Sin memoria (Traigo mi propia SD)":
        st.sidebar.error("No puedes enviar el pedido, excediste la memoria.")
    else:
        # Armar el mensaje de WhatsApp
        lista_texto = ", ".join(juegos_seleccionados)
        mensaje = f"¡Hola Gamefix! 👋 Quiero agendar una instalación de Nintendo Switch.\n\n"
        mensaje += f"📦 *Opción elegida:* {opcion_memoria}\n"
        mensaje += f"💾 *Espacio ocupado:* {espacio_usado:.1f} GB\n"
        mensaje += f"🎮 *Juegos seleccionados ({len(juegos_seleccionados)}):* {lista_texto}\n\n"
        mensaje += f"💵 *Costo Total Cotizado:* ${costo_total} MXN\n\n"
        mensaje += "¿Me proporcionas el link de pago de Mercado Pago o los datos de depósito?"
        
        # NUMERO DE WHATSAPP DEL TALLER (Cambiar aquí)
        numero_whatsapp = "529980000000" # Formato internacional sin símbolo +, ej. 52 para México
        
        # Crear URL codificada
        url_whatsapp = f"https://wa.me/{numero_whatsapp}?text={urllib.parse.quote(mensaje)}"
        
        st.sidebar.success("Haz clic en el enlace de abajo para abrir WhatsApp:")
        st.sidebar.markdown(f"[👉 **CONFIRMAR PEDIDO AQUÍ**]({url_whatsapp})")

