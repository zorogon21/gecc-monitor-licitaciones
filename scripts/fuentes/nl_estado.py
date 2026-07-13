# -*- coding: utf-8 -*-
"""
nl_estado.py — Fuente: Licitaciones públicas de las dependencias centrales
del Gobierno del Estado de Nuevo León.

https://nl.gob.mx/es/licitaciones-dependencias-centrales es una página
Drupal renderizada en el servidor (no requiere navegador): lista, por año,
cada licitación con su título+objeto y su "Vigencia: DD [de MES] al DD de
MES de AAAA" ya en el HTML — la mejor fuente encontrada en el
reconocimiento de Nuevo León, comparable a las mejores de Guanajuato.

La "Vigencia" trae dos formatos posibles en este sitio:
- "01 al 20 de julio de 2026" (mismo mes de inicio y fin)
- "19 de junio al 09 de julio de 2026" (meses distintos)
Se usa el inicio como fecha_publicacion y el fin como fecha_limite.
"""

import re
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

URL = "https://nl.gob.mx/es/licitaciones-dependencias-centrales"
REQUEST_TIMEOUT = 30
FUENTE = "Licitaciones Públicas — Gobierno del Estado de Nuevo León"
COMPRADOR = "Gobierno del Estado de Nuevo León"
UBICACION = "Nuevo León"

ITEM_RE = re.compile(r'<li><a href="([^"]+)">([^<]+)</a><br>Vigencia:\s*([^<]+?)\s*<br')

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11,
    "diciembre": 12,
}
# "19 de junio al 09 de julio de 2026"
VIGENCIA_DOS_MESES_RE = re.compile(
    r"(\d{1,2})\s+de\s+(\w+)\s+al\s+(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})", re.IGNORECASE
)
# "01 al 20 de julio de 2026"
VIGENCIA_UN_MES_RE = re.compile(
    r"(\d{1,2})\s+al\s+(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})", re.IGNORECASE
)


def _fecha(anio, mes_txt, dia):
    mes = MESES.get(mes_txt.lower())
    if not mes:
        return ""
    try:
        return datetime(int(anio), mes, int(dia), tzinfo=timezone.utc).isoformat()
    except ValueError:
        return ""


def _parsear_vigencia(texto_vigencia):
    """Regresa (fecha_publicacion, fecha_limite) en ISO 8601, o ('', '') si no se pudo interpretar."""
    m = VIGENCIA_DOS_MESES_RE.search(texto_vigencia)
    if m:
        dia_ini, mes_ini, dia_fin, mes_fin, anio = m.groups()
        return _fecha(anio, mes_ini, dia_ini), _fecha(anio, mes_fin, dia_fin)

    m = VIGENCIA_UN_MES_RE.search(texto_vigencia)
    if m:
        dia_ini, dia_fin, mes, anio = m.groups()
        return _fecha(anio, mes, dia_ini), _fecha(anio, mes, dia_fin)

    return "", ""


def obtener_licitaciones():
    """Devuelve (licitaciones, error), mismo formato que las demás fuentes."""
    req = Request(URL, headers={"User-Agent": "GECC-Monitor-Licitaciones/1.0"})
    try:
        with urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            html = resp.read().decode("utf-8", errors="replace").replace("&nbsp;", " ")
    except (URLError, HTTPError, TimeoutError) as e:
        return [], f"Error al consultar el portal del Estado de Nuevo León: {e}"

    licitaciones = []
    vistos = set()
    for link, titulo, vigencia in ITEM_RE.findall(html):
        if link in vistos:
            continue
        vistos.add(link)

        fecha_publicacion, fecha_limite = _parsear_vigencia(vigencia)
        slug = link.rstrip("/").split("nl.gob.mx/", 1)[-1].replace("/", "-")

        licitaciones.append({
            "ocid": f"nl-estado-{slug}",
            "titulo": titulo.strip(),
            "descripcion": "",
            "comprador": COMPRADOR,
            "ubicacion": UBICACION,
            "fecha_publicacion": fecha_publicacion,
            "fecha_limite": fecha_limite,
            "link": link,
            "fuente": FUENTE,
        })
    return licitaciones, None
