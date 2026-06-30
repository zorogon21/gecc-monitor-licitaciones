# -*- coding: utf-8 -*-
"""
uriangato.py — Fuente: Convocatorias y Licitaciones del Municipio de
Uriangato, Gto.

https://uriangato.gob.mx/web/tramites/convocatorias es una página
estática (HTML renderizado en servidor) con tarjetas agrupadas por año;
cada licitación trae tipo (badge), título, fecha (dd/mm/aaaa) y link a PDF
ya en el listado — no requiere navegador ni entrar a cada detalle.

No hay una fecha límite distinta a la fecha de publicación en este
listado, así que 'fecha_limite' se deja vacía.
"""

import hashlib
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

URL = "https://uriangato.gob.mx/web/tramites/convocatorias"
REQUEST_TIMEOUT = 30
FUENTE = "Convocatorias y Licitaciones — Municipio de Uriangato"
COMPRADOR = "Municipio de Uriangato, Guanajuato"
UBICACION = "Guanajuato"

ITEM_RE = re.compile(r'<li class="list-group-item[^"]*".*?</li>', re.DOTALL)
TITULO_RE = re.compile(r'fw-semibold">([^<]*)</div>')
FECHA_RE = re.compile(r"bi-calendar-event[^<]*</i>\s*(\d{2}/\d{2}/\d{4})")
LINK_RE = re.compile(r'href="([^"]+\.pdf)"', re.IGNORECASE)


def _fecha_iso(fecha_ddmmyyyy):
    try:
        dia, mes, anio = fecha_ddmmyyyy.split("/")
        return f"{anio}-{mes}-{dia}T00:00:00Z"
    except ValueError:
        return ""


def obtener_licitaciones():
    """Devuelve (licitaciones, error), mismo formato que las demás fuentes."""
    req = Request(URL, headers={"User-Agent": "GECC-Monitor-Licitaciones/1.0"})
    try:
        with urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except (URLError, HTTPError, TimeoutError) as e:
        return [], f"Error al consultar el portal de Uriangato: {e}"

    licitaciones = []
    for item in ITEM_RE.findall(html):
        titulo_m = TITULO_RE.search(item)
        if not titulo_m:
            continue
        titulo = titulo_m.group(1).strip()
        link_m = LINK_RE.search(item)
        link = link_m.group(1) if link_m else ""
        fecha_m = FECHA_RE.search(item)
        fecha_publicacion = _fecha_iso(fecha_m.group(1)) if fecha_m else ""

        identificador = link or titulo
        ocid = "uriangato-" + hashlib.md5(identificador.encode("utf-8")).hexdigest()[:12]

        licitaciones.append({
            "ocid": ocid,
            "titulo": titulo,
            "descripcion": "",
            "comprador": COMPRADOR,
            "ubicacion": UBICACION,
            "fecha_publicacion": fecha_publicacion,
            "fecha_limite": "",
            "link": link,
            "fuente": FUENTE,
        })
    return licitaciones, None
