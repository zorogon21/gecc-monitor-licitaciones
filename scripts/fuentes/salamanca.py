# -*- coding: utf-8 -*-
"""
salamanca.py — Fuente: Licitaciones del Municipio de Salamanca, Gto.

https://gaceta.salamanca.gob.mx/publico/licitaciones muestra un grid de
tarjetas. El JavaScript de la página solo filtra tarjetas que el SERVIDOR
ya puso en el HTML (confirmado leyendo indexPublicoLicitaciones.js: no
hace ningún fetch/AJAX, solo querySelectorAll sobre el DOM existente), así
que es una página estática para efectos de scraping.

El portal no expone fecha de publicación ni fecha límite en ningún lado de
la tarjeta (ni en el HTML de las tarjetas pobladas que se pudieron
inspeccionar en la página hermana de "convocatorias", que usa el mismo
template) — así que ambos campos de fecha se dejan vacíos.
"""

import hashlib
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

URL = "https://gaceta.salamanca.gob.mx/publico/licitaciones"
REQUEST_TIMEOUT = 30
FUENTE = "Licitaciones — Municipio de Salamanca"
COMPRADOR = "Municipio de Salamanca, Guanajuato"
UBICACION = "Guanajuato"

TARJETA_RE = re.compile(r'<article class="sp-card"[^>]*>.*?</article>', re.DOTALL)
TITULO_RE = re.compile(r'sp-card-title">([^<]*)</h3>')
DESC_RE = re.compile(r'sp-card-description">([^<]*)</p>')
LINK_RE = re.compile(r'sp-card-actions">\s*<a href="([^"]+)"')


def obtener_licitaciones():
    """Devuelve (licitaciones, error), mismo formato que las demás fuentes."""
    req = Request(URL, headers={"User-Agent": "GECC-Monitor-Licitaciones/1.0"})
    try:
        with urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except (URLError, HTTPError, TimeoutError) as e:
        return [], f"Error al consultar el portal de Salamanca: {e}"

    licitaciones = []
    for tarjeta in TARJETA_RE.findall(html):
        titulo_m = TITULO_RE.search(tarjeta)
        if not titulo_m:
            continue
        titulo = titulo_m.group(1).strip()
        desc_m = DESC_RE.search(tarjeta)
        descripcion = desc_m.group(1).strip() if desc_m else ""
        link_m = LINK_RE.search(tarjeta)
        link = link_m.group(1) if link_m else ""

        identificador = (link or titulo)
        ocid = "salamanca-" + hashlib.md5(identificador.encode("utf-8")).hexdigest()[:12]

        licitaciones.append({
            "ocid": ocid,
            "titulo": titulo,
            "descripcion": descripcion,
            "comprador": COMPRADOR,
            "ubicacion": UBICACION,
            "fecha_publicacion": "",
            "fecha_limite": "",
            "link": link,
            "fuente": FUENTE,
        })
    return licitaciones, None
