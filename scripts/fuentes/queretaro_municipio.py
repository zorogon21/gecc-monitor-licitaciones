# -*- coding: utf-8 -*-
"""
queretaro_municipio.py — Fuente: Licitaciones Públicas Municipales del
Municipio de Querétaro (capital).

https://municipiodequeretaro.gob.mx/licitaciones/publicas-municipales/ es
HTML estático generado por el WordPress Page Builder (Visual Composer) —
no requiere navegador. En el reconocimiento inicial el texto visible junto
a cada PDF parecía ser solo "Ver Documento" (genérico), pero cada
licitación en realidad está en su propia columna con el número de
expediente (h3) y la descripción completa del objeto (p) justo antes del
link — hay que leer por bloque de columna, no solo el texto del link.

No hay una fecha de publicación confiable en ningún lado: se probaron el
timestamp "vc_custom_<epoch_ms>" que el Page Builder graba por bloque y
la carpeta año/mes de la URL del PDF, y ambos contradicen en varios casos
el propio número de expediente (ej. un "LPM/SOPM/003/23" con timestamp de
2022, o un archivo "2025-..." guardado en una carpeta "/2021/11/"). Usar
cualquiera de los dos como fecha_publicacion arriesgaba podar por
antigüedad (filtrar_vigentes) licitaciones que en realidad seguían
vigentes, así que se deja vacía en vez de inventar una fecha — el año sí
queda visible para quien lea la tarjeta porque va dentro del propio
número de expediente en el título (ej. "LPM/SOPM/003/23"). Tampoco hay
fecha límite en ningún lado, así que también se deja vacía.

Nota: la sub-página "publicas-nacionales" del mismo sitio solo llega
hasta 2023 (desactualizada) — por eso no se incluye aquí, solo
"publicas-municipales", que sí tiene contenido de 2025.
"""

import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

URL = "https://municipiodequeretaro.gob.mx/licitaciones/publicas-municipales/"
REQUEST_TIMEOUT = 30
FUENTE = "Licitaciones Públicas Municipales — Municipio de Querétaro"
COMPRADOR = "Municipio de Querétaro"
UBICACION = "Querétaro"

DIVISOR_COLUMNA = '<div class="wpb_column vc_column_container vc_col-sm-4'
CODIGO_RE = re.compile(r"<h3[^>]*><strong>(?:<img[^>]*>)?\s*([^<]+?)\s*</strong></h3>", re.DOTALL)
TITULO_RE = re.compile(r"</h3>\s*<p[^>]*>([^<]*)</p>", re.DOTALL)
LINK_RE = re.compile(r'href="([^"]+\.pdf)"')


def obtener_licitaciones():
    """Devuelve (licitaciones, error), mismo formato que las demás fuentes."""
    req = Request(URL, headers={"User-Agent": "GECC-Monitor-Licitaciones/1.0"})
    try:
        with urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except (URLError, HTTPError, TimeoutError) as e:
        return [], f"Error al consultar el portal del Municipio de Querétaro: {e}"

    licitaciones = []
    vistos = set()
    for bloque in html.split(DIVISOR_COLUMNA)[1:]:
        codigo_m = CODIGO_RE.search(bloque)
        link_m = LINK_RE.search(bloque)
        if not codigo_m or not link_m:
            continue  # columna sin licitación (encabezado, imagen suelta, etc.)

        link = link_m.group(1)
        if link in vistos:
            continue
        vistos.add(link)

        codigo = codigo_m.group(1).strip()
        titulo_m = TITULO_RE.search(bloque)
        descripcion_objeto = titulo_m.group(1).strip() if titulo_m else ""

        licitaciones.append({
            "ocid": "qro-mpio-" + re.sub(r"[^A-Za-z0-9]+", "-", codigo).strip("-"),
            "titulo": f"{codigo} — {descripcion_objeto}" if descripcion_objeto else codigo,
            "descripcion": descripcion_objeto,
            "comprador": COMPRADOR,
            "ubicacion": UBICACION,
            "fecha_publicacion": "",
            "fecha_limite": "",
            "link": link,
            "fuente": FUENTE,
        })
    return licitaciones, None
