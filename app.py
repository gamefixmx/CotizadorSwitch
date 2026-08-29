# -*- coding: utf-8 -*-
"""
Gamefix - Cotizador de instalacion de juegos para Nintendo Switch.

Version pensada para celular:
  * El resumen (memoria, espacio, total y boton de WhatsApp) va fijo arriba,
    siempre visible mientras se eligen juegos. Ya no hay barra lateral.
  * 3 cartuchos por fila tambien en el telefono.
  * Los iconos se piden en miniatura (~11 KB en vez de ~750 KB) y solo se
    descargan los que entran en pantalla.
  * Un solo toque para enviar el pedido por WhatsApp.
"""

import base64
import os
import urllib.parse

import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# CONFIGURACION DEL NEGOCIO
# ---------------------------------------------------------------------------

PRECIO_SIN_MEMORIA = 1200
PRECIO_128GB = 1500
PRECIO_256GB = 2200
COSTO_JUEGO_EXTRA = 100
JUEGOS_INCLUIDOS = 10

CAPACIDAD_128 = 119.0
CAPACIDAD_256 = 238.0
CAPACIDAD_PROPIA = 500.0

NUMERO_WHATSAPP = "529845208305"

SHEET_ID = "1NVQeuswZ0odOah7wrFMENsdx-uSYU7BhsVjnmFLQnpI"

# Cuantos juegos se dibujan de golpe. Menos = carga mas rapido.
POR_TANDA = 60

# Ancho al que se piden los iconos (px). 200 se ve bien y pesa ~11 KB.
ANCHO_ICONO = 200

# Largo maximo del enlace de WhatsApp. Pasado eso, la lista de juegos se
# recorta: hay telefonos que truncan las URLs muy largas. 15000 alcanza para
# unos 140 juegos, muy por encima de un pedido normal.
LARGO_MAXIMO_URL = 15000

OPCIONES_MEMORIA = {
    "Traigo mi SD": (PRECIO_SIN_MEMORIA, CAPACIDAD_PROPIA, "Sin memoria (Traigo mi propia SD)"),
    "128 GB": (PRECIO_128GB, CAPACIDAD_128, "Comprar Memoria 128 GB"),
    "256 GB": (PRECIO_256GB, CAPACIDAD_256, "Comprar Memoria 256 GB"),
}

st.set_page_config(page_title="Gamefix - Cotizador Switch", page_icon="🎮",
                   layout="centered", initial_sidebar_state="collapsed")


# ---------------------------------------------------------------------------
# ESTILOS
# ---------------------------------------------------------------------------

@st.cache_data
def imagen_base64(ruta, _marca_de_tiempo):
    """Lee una imagen y la deja lista para incrustar en el CSS.

    La marca de tiempo entra en la clave del cache: si cambias cartucho.png,
    la app toma el nuevo sin tener que reiniciarla.
    """
    if not os.path.exists(ruta):
        return ""
    with open(ruta, "rb") as f:
        return base64.b64encode(f.read()).decode()


def leer_imagen(ruta):
    marca = os.path.getmtime(ruta) if os.path.exists(ruta) else 0
    return imagen_base64(ruta, marca)


CARTUCHO_B64 = leer_imagen("cartucho.png")


def fondo_de_la_barra():
    """CSS del fondo de la barra fija.

    La barra tiene que tapar lo que pasa por debajo al hacer scroll, o sea que
    necesita un color solido, y ese color depende del tema del visitante.

    Calcularlo en Python falla si el cliente cambia su telefono a modo oscuro
    con la pagina abierta: el CSS ya se envio y se queda del color viejo. Por
    eso se usa light-dark(), que resuelve el color en el navegador siguiendo el
    color-scheme que Streamlit pone en el contenedor. La primera linea es el
    respaldo para navegadores viejos que no conocen light-dark().
    """
    propio = st.get_option("theme.backgroundColor")
    if propio:                      # tema fijo en .streamlit/config.toml
        return "background: %s;" % propio

    try:
        respaldo = "#FFFFFF" if st.context.theme.type == "light" else "#0E1117"
    except Exception:
        respaldo = "#0E1117"

    return ("background: %s;\n      background: light-dark(#FFFFFF, #0E1117);"
            % respaldo)


FONDO_BARRA = fondo_de_la_barra()

if CARTUCHO_B64:
    # Diseno original: la portada abajo y el PNG del cartucho encima, para que
    # el marco del cartucho le quede por delante a la imagen.
    CSS_TARJETA = """
  .cartucho {
      width: 100%; aspect-ratio: 351/508; position: relative; margin-bottom: 6px;
  }
  /* La ventana del cartucho mide 300x300 px dentro de un PNG de 351x508,
     o sea left 7.41% / top 26.38% / 86.04% x 59.25%. La portada se dibuja un
     pelo mas grande para que se meta por debajo del marco: asi no queda una
     franja del fondo asomando (en tema claro se veia blanca). El marco va
     encima, con lo cual ese sobrante no se ve. */
  .cartucho .portada {
      position: absolute; left: 6.9%; top: 25.7%; width: 87.2%; height: 60.6%;
      object-fit: cover; z-index: 1;
  }
  .cartucho .marco {
      position: absolute; inset: 0; z-index: 2;
      background-image: url('data:image/png;base64,__B64__');
      background-size: 100% 100%; background-repeat: no-repeat;
  }
  .cartucho .titulo {
      position: absolute; top: 42%; left: 50%; transform: translate(-50%,-50%);
      width: 80%; text-align: center; font-family: 'Arial Black', Impact, sans-serif;
      font-size: 10px; color: #111; line-height: 1.15; word-wrap: break-word;
      z-index: 3;
  }
""".replace("__B64__", CARTUCHO_B64)
else:
    # Sin cartucho.png al lado: portada sola, cuadrada. Se ve limpio igual.
    CSS_TARJETA = """
  .cartucho {
      width: 100%; aspect-ratio: 1/1; position: relative; margin-bottom: 6px;
      border-radius: 8px; overflow: hidden;
      background: linear-gradient(180deg,#3a3f52 0%,#2b2f3d 100%);
  }
  .cartucho .portada { width: 100%; height: 100%; object-fit: cover; display: block; }
  .cartucho .marco { display: none; }
  .cartucho .titulo {
      position: absolute; inset: 0; display: flex; align-items: center;
      justify-content: center; text-align: center; padding: 8px;
      font-weight: 800; font-size: 11px; color: #e8eaf2; line-height: 1.2;
  }
"""

st.markdown("""
<style>
  /* ---------- barra fija de resumen ----------
     El sticky tiene que ir en el DIV PADRE del contenedor: si se pone en el
     contenedor mismo, su padre mide lo mismo que el y no hay por donde
     deslizarse. Por eso el :has(). */
  div[data-testid="stVerticalBlock"] > div:has(> div[class*="st-key-barra_fija"]) {
      position: sticky;
      top: 0;
      z-index: 999;
      %(fondo)s
      padding-top: 8px;
      border-bottom: 1px solid rgba(140,140,160,.35);
      box-shadow: 0 8px 16px -12px rgba(0,0,0,.75);
  }
  div[class*="st-key-barra_fija"] { gap: 6px; padding-bottom: 8px; }

  /* La barra de Streamlit taparia el resumen: esta pagina es para clientes. */
  header[data-testid="stHeader"] { display: none; }

  .resumen {
      display: flex; justify-content: space-between; align-items: baseline;
      font-size: 14px; margin: 2px 0 4px;
  }
  .resumen .total { font-size: 19px; font-weight: 800; }
  .resumen .lleno { color: #ff5f56; font-weight: 700; }

  /* ---------- 3 columnas tambien en celular ---------- */
  @media (max-width: 640px) {
      section[data-testid="stMain"] .stMainBlockContainer { padding: 12px 10px 60px; }
      div[data-testid="stHorizontalBlock"] {
          flex-wrap: nowrap !important;
          gap: 8px !important;
      }
      div[data-testid="stColumn"] {
          min-width: 0 !important;
          width: auto !important;
          flex: 1 1 0 !important;
      }
  }

  /* ---------- tarjeta de juego ---------- */
%(tarjeta)s
  .nombre-juego {
      font-size: 12px; font-weight: 700; line-height: 1.25;
      margin: 0 0 2px; overflow-wrap: anywhere;
  }
  .peso-juego { font-size: 11px; opacity: .7; margin-bottom: 4px; }

  /* checkbox mas compacto y legible en celular */
  div[data-testid="stCheckbox"] label { font-size: 12px !important; gap: 4px !important; }
  div[data-testid="stCheckbox"] { margin-bottom: 2px; }
</style>
""" % {"tarjeta": CSS_TARJETA, "fondo": FONDO_BARRA}, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# DATOS
# ---------------------------------------------------------------------------

@st.cache_data(ttl=300)
def cargar_juegos():
    url = "https://docs.google.com/spreadsheets/d/%s/export?format=csv" % SHEET_ID
    try:
        df = pd.read_csv(url)
    except Exception:
        # Respaldo: el CSV que genera unificar_catalogo.py, si esta al lado
        local = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "juegos_switch_unificado.csv")
        if not os.path.exists(local):
            return pd.DataFrame()
        df = pd.read_csv(local)

    df = df.dropna(subset=["Nombre"]).copy()
    df["Nombre"] = df["Nombre"].astype(str).str.strip()
    df["Peso_GB"] = pd.to_numeric(df["Peso_GB"], errors="coerce").fillna(0.0)
    if "URL_Portada" not in df.columns:
        df["URL_Portada"] = ""
    df["URL_Portada"] = df["URL_Portada"].fillna("").astype(str).str.strip()
    if "Incluye_DLC" not in df.columns:
        df["Incluye_DLC"] = ""
    df["Incluye_DLC"] = df["Incluye_DLC"].fillna("").astype(str).str.strip()
    df["clave"] = ["j%d" % i for i in range(len(df))]
    return df.reset_index(drop=True)


def miniatura(url):
    """Pide el icono en chico a un redimensionador publico.

    El CDN de Nintendo no acepta parametros de tamano y sirve JPG de ~750 KB.
    wsrv.nl devuelve el mismo icono en WebP de ~11 KB. Si el servicio fallara,
    el onerror de la etiqueta <img> vuelve a la imagen original.
    """
    if not url:
        return ""
    return ("https://wsrv.nl/?url=%s&w=%d&h=%d&fit=cover&output=webp&q=80"
            % (urllib.parse.quote(url, safe=""), ANCHO_ICONO, ANCHO_ICONO))


df = cargar_juegos()

if df.empty:
    st.error("No pude cargar el catalogo de juegos. Revisa la conexion o la hoja de Google.")
    st.stop()


# ---------------------------------------------------------------------------
# ESTADO: que hay en el carrito ANTES de dibujar nada
# ---------------------------------------------------------------------------
# Streamlit vuelve a correr el script completo en cada clic, y el estado de los
# checkboxes ya esta en session_state. Por eso podemos calcular el resumen
# aqui arriba y dibujar la barra fija antes que el catalogo.

seleccion = df[[bool(st.session_state.get("chk_" + k)) for k in df["clave"]]]
n_juegos = len(seleccion)
espacio_usado = float(seleccion["Peso_GB"].sum())

etiqueta_memoria = st.session_state.get("memoria", "Traigo mi SD")
costo_base, capacidad_max, memoria_larga = OPCIONES_MEMORIA[etiqueta_memoria]

juegos_extra = max(0, n_juegos - JUEGOS_INCLUIDOS)
costo_total = costo_base + juegos_extra * COSTO_JUEGO_EXTRA
sin_espacio = espacio_usado > capacidad_max


def armar_mensaje(limite=None):
    """El pedido, con los juegos en lista numerada (uno por renglon)."""
    juegos = list(zip(seleccion["Nombre"].tolist(), seleccion["Peso_GB"].tolist()))
    recortados = juegos[:limite] if limite else juegos

    renglones = ["%d. %s (%.2f GB)" % (i, nombre, peso)
                 for i, (nombre, peso) in enumerate(recortados, start=1)]
    if limite and len(juegos) > limite:
        renglones.append("...y %d juegos mas" % (len(juegos) - limite))
    lista = "\n".join(renglones)

    m = "¡Hola Gamefix! 👋 Quiero agendar una instalacion de Nintendo Switch.\n\n"
    m += "📦 *Opcion elegida:* %s\n" % memoria_larga
    m += "💾 *Espacio ocupado:* %.1f GB\n" % espacio_usado
    m += "💵 *Costo total cotizado:* $%d MXN\n\n" % costo_total
    m += "🎮 *Juegos seleccionados (%d):*\n%s\n\n" % (n_juegos, lista)
    m += "¿Me proporcionas el link de pago de Mercado Pago o los datos de deposito?"
    return m


def url_de_whatsapp():
    """Enlace con el pedido ya escrito.

    Una lista larga puede generar una URL enorme y algunos telefonos la cortan,
    asi que si se pasa del limite se recorta la lista por pasos.
    """
    url = ""
    for limite in (None, 80, 50, 30):
        url = "https://wa.me/%s?text=%s" % (
            NUMERO_WHATSAPP, urllib.parse.quote(armar_mensaje(limite)))
        if len(url) <= LARGO_MAXIMO_URL:
            break
    return url


url_whatsapp = url_de_whatsapp()


# ---------------------------------------------------------------------------
# BARRA FIJA
# ---------------------------------------------------------------------------

with st.container(key="barra_fija"):
    st.segmented_control(
        "Memoria", list(OPCIONES_MEMORIA.keys()), key="memoria",
        default="Traigo mi SD", label_visibility="collapsed", width="stretch",
    )

    if sin_espacio:
        aviso = '<span class="lleno">%.1f / %.0f GB - te pasaste</span>' % (
            espacio_usado, capacidad_max)
    else:
        aviso = "%.1f / %.0f GB" % (espacio_usado, capacidad_max)

    st.markdown(
        '<div class="resumen"><span>🛒 %d %s &nbsp;·&nbsp; %s</span>'
        '<span class="total">$%d</span></div>'
        % (n_juegos, "juego" if n_juegos == 1 else "juegos", aviso, costo_total),
        unsafe_allow_html=True,
    )
    st.progress(min(espacio_usado / capacidad_max, 1.0) if capacidad_max else 0.0)

    if n_juegos == 0:
        st.button("Elige tus juegos para cotizar", disabled=True, width="stretch")
    elif sin_espacio:
        st.button("Quita juegos: no caben en %s" % etiqueta_memoria,
                  disabled=True, width="stretch")
    else:
        st.link_button("📲 Enviar pedido por WhatsApp", url_whatsapp,
                       type="primary", width="stretch")


# ---------------------------------------------------------------------------
# CARRITO
# ---------------------------------------------------------------------------

if n_juegos:
    with st.expander("Ver mi carrito (%d)" % n_juegos):
        for _, fila in seleccion.iterrows():
            c1, c2 = st.columns([5, 1], vertical_alignment="center")
            c1.write("%s  ·  %.2f GB" % (fila["Nombre"], fila["Peso_GB"]))
            if c2.button("Quitar", key="quitar_" + fila["clave"]):
                st.session_state["chk_" + fila["clave"]] = False
                st.rerun()
        if juegos_extra:
            st.caption("Los primeros %d juegos van incluidos. Llevas %d extra "
                       "(+$%d c/u)." % (JUEGOS_INCLUIDOS, juegos_extra, COSTO_JUEGO_EXTRA))
        else:
            st.caption("Te quedan %d juegos incluidos en el precio base."
                       % (JUEGOS_INCLUIDOS - n_juegos))


# ---------------------------------------------------------------------------
# CATALOGO
# ---------------------------------------------------------------------------

st.caption("Los primeros %d juegos van incluidos en el precio. Del %davo en "
           "adelante, +$%d cada uno." % (JUEGOS_INCLUIDOS, JUEGOS_INCLUIDOS + 1,
                                         COSTO_JUEGO_EXTRA))

busqueda = st.text_input("Buscar juego", "", placeholder="🔍 Buscar juego por nombre...",
                         label_visibility="collapsed").strip().lower()

if busqueda:
    visibles = df[df["Nombre"].str.lower().str.contains(busqueda, regex=False)]
else:
    visibles = df

if "tanda" not in st.session_state:
    st.session_state.tanda = POR_TANDA

# Al cambiar la busqueda se vuelve a empezar por la primera tanda: si no, una
# busqueda de una sola letra dibujaria cientos de tarjetas de golpe.
if st.session_state.get("busqueda_previa") != busqueda:
    st.session_state.busqueda_previa = busqueda
    st.session_state.tanda = POR_TANDA

mostrar = visibles.head(st.session_state.tanda)

if visibles.empty:
    st.info("No encontre ningun juego con ese nombre.")

COLUMNAS = 3
filas_visibles = list(mostrar.iterrows())

# Se crean columnas por cada renglon (y no tres columnas larguisimas) para que
# las tarjetas queden alineadas aunque unos nombres ocupen dos lineas.
for inicio in range(0, len(filas_visibles), COLUMNAS):
    columnas = st.columns(COLUMNAS)

    for columna, (_, fila) in zip(columnas, filas_visibles[inicio:inicio + COLUMNAS]):
        with columna:
            nombre = fila["Nombre"]
            portada = fila["URL_Portada"]

            if portada:
                # src = miniatura ligera; si el redimensionador falla, el
                # onerror cae a la imagen original de Nintendo.
                html = ('<div class="cartucho">'
                        '<img class="portada" loading="lazy" decoding="async" src="%s" '
                        'onerror="this.onerror=null;this.src=\'%s\';" alt="">'
                        '<div class="marco"></div>'
                        '</div>') % (miniatura(portada), portada)
            else:
                html = ('<div class="cartucho"><div class="marco"></div>'
                        '<div class="titulo">%s</div></div>') % nombre

            st.markdown(html, unsafe_allow_html=True)
            st.markdown('<div class="nombre-juego">%s</div>' % nombre,
                        unsafe_allow_html=True)

            detalle = "%.2f GB" % fila["Peso_GB"]
            if fila["Incluye_DLC"].lower() in ("si", "sí"):
                detalle += " · DLC"
            st.markdown('<div class="peso-juego">%s</div>' % detalle,
                        unsafe_allow_html=True)

            marcado = bool(st.session_state.get("chk_" + fila["clave"]))
            st.checkbox("Agregado ✓" if marcado else "Agregar",
                        key="chk_" + fila["clave"])

if len(mostrar) < len(visibles):
    faltan = len(visibles) - len(mostrar)
    if st.button("Ver %d juegos más" % min(POR_TANDA, faltan), width="stretch"):
        st.session_state.tanda += POR_TANDA
        st.rerun()
    st.caption("Mostrando %d de %d. Usa el buscador de arriba para encontrar "
               "uno directo." % (len(mostrar), len(visibles)))
