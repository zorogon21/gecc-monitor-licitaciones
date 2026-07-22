# -*- coding: utf-8 -*-
"""
slp_capital.py — Fuente: Licitaciones Públicas del Municipio de San Luis
Potosí (capital).

https://sitio.sanluis.gob.mx/SanLuisPotoSi/LicitacionesPublicas2 es HTML
estático (no requiere navegador): cada licitación es un bloque
'<li class="accordion block">' con campos ya etiquetados en el propio
HTML — Titulo, Descripción, Fecha de Publicación (DD/MM/AAAA) y
Presentación y Apertura de Propuestas (DD/MM/AAAA HH:MM:SS), esta última
usada como fecha límite real. La mejor fuente encontrada en el
reconocimiento de San Luis Potosí — comparable a Nuevo León estatal.

Unos pocos bloques (procesos muy recién publicados) todavía no traen
Fecha de Publicación ni Presentación y Apertura de Propuestas; en ese
caso ambos campos se dejan vacíos en vez de inventarlos.
"""

import re
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

URL = "https://sitio.sanluis.gob.mx/SanLuisPotoSi/LicitacionesPublicas2"
REQUEST_TIMEOUT = 30
FUENTE = "Licitaciones Públicas — Municipio de San Luis Potosí"
COMPRADOR = "Municipio de San Luis Potosí"
UBICACION = "San Luis Potosí"

DIVISOR_BLOQUE = '<li class="accordion block">'
CODIGO_RE = re.compile(r'id="headTituloScroll([^"]+)"')
LINK_RE = re.compile(r'href="([^"]+\.pdf)"')
FECHA_RE = re.compile(r"(\d{2})/(\d{2})/(\d{4})(?:\s+(\d{2}):(\d{2}):(\d{2}))?")


def _valor_campo(bloque, etiqueta):
    m = re.search(
        re.escape(etiqueta) + r"\s*</span>\s*</div>\s*<div[^>]*>\s*<span[^>]*>\s*([^<]*)</span>",
        bloque,
        re.DOTALL,
    )
    return m.group(1).strip() if m else ""


def _fecha_iso(texto_fecha):
    m = FECHA_RE.search(texto_fecha or "")
    if not m:
        return ""
    dia, mes, anio, hora, minuto, segundo = m.groups()
    try:
        return datetime(
            int(anio), int(mes), int(dia),
            int(hora or 0), int(minuto or 0), int(segundo or 0),
            tzinfo=timezone.utc,
        ).isoformat()
    except ValueError:
        return ""


def obtener_licitaciones():
    """Devuelve (licitaciones, error), mismo formato que las demás fuentes."""
    req = Request(URL, headers={"User-Agent": "GECC-Monitor-Licitaciones/1.0"})
    try:
        with urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except (URLError, HTTPError, TimeoutError) as e:
        return [], f"Error al consultar el portal del Municipio de San Luis Potosí: {e}"

    licitaciones = []
    for bloque in html.split(DIVISOR_BLOQUE)[1:]:
        codigo_m = CODIGO_RE.search(bloque)
        if not codigo_m:
            continue
        codigo = codigo_m.group(1).strip()

        titulo = _valor_campo(bloque, "Titulo:")
        if not titulo:
            continue

        descripcion = _valor_campo(bloque, "Descripción:")
        fecha_publicacion = _fecha_iso(_valor_campo(bloque, "Fecha de Publicación:"))
        fecha_limite = _fecha_iso(_valor_campo(bloque, "Presentación y Apertura de Propuestas:"))

        link_m = LINK_RE.search(bloque)
        link = link_m.group(1) if link_m else ""

        licitaciones.append({
            "ocid": f"slp-mpio-{codigo}",
            "titulo": f"{codigo} — {titulo}",
            "descripcion": descripcion,
            "comprador": COMPRADOR,
            "ubicacion": UBICACION,
            "fecha_publicacion": fecha_publicacion,
            "fecha_limite": fecha_limite,
            "link": link,
            "fuente": FUENTE,
        })
    return licitaciones, None
