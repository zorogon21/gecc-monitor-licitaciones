# -*- coding: utf-8 -*-
"""
sanpedro.py — Fuente: Licitaciones del Municipio de San Pedro Garza García, N.L.

https://licitaciones.sanpedro.gob.mx/default.aspx es una app ASP.NET
Web Forms; en el reconocimiento inicial parecía requerir JavaScript/
postback porque una búsqueda con expresiones regulares muy específicas no
encontró nada. Al revisar con más cuidado, el HTML que regresa la primera
carga (sin ningún postback) SÍ trae, para cada procedimiento, un bloque
'accordion-container' con título completo, número de expediente,
descripción, tipo de procedimiento, solicitante, y las fechas/PDFs de
cada etapa del concurso — todo servido en el HTML inicial. No hace falta
navegador.

No hay una etapa que represente de forma confiable la fecha límite de
presentación de propuestas (las etapas presentes varían según qué tan
avanzado esté cada concurso), así que 'fecha_limite' se deja vacía; se
usa la fecha de la etapa "Convocatoria" como fecha_publicacion.
"""

import re
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

URL = "https://licitaciones.sanpedro.gob.mx/default.aspx"
REQUEST_TIMEOUT = 30
FUENTE = "Licitaciones — Municipio de San Pedro Garza García"
UBICACION = "Nuevo León"

TAG_RE = re.compile(r"<[^>]+>")
TITULO_RE = re.compile(r"class='accordion-titulo'><p>(.*?)<span class='toggle-icon'", re.DOTALL)
NUMERO_RE = re.compile(r"N&#176;\s*([A-Z0-9\-/]+)", re.IGNORECASE)
DESC_RE = re.compile(r"DESCRIPCION:\s*(.*?)</p>", re.DOTALL)
TIPO_RE = re.compile(r"TIPO DE PROCEDIMIENTO:\s*(.*?)</p>")
SOLICITANTE_RE = re.compile(r"<td>\s*Solicitante\s*</th>\s*<td>([^<]*)</th>", re.IGNORECASE)
CONVOCATORIA_RE = re.compile(
    r"<i[^>]*chevron-right[^>]*></i>&nbsp;Convocatoria</td>\s*<td[^>]*>([^<]*)</td>\s*<td[^>]*><a href='([^']+)'",
    re.IGNORECASE,
)

MESES = {
    "ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6,
    "jul": 7, "ago": 8, "sep": 9, "oct": 10, "nov": 11, "dic": 12,
}
FECHA_RE = re.compile(r"(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})")


def _limpiar_texto(html_fragmento):
    texto = TAG_RE.sub(" ", html_fragmento or "")
    texto = texto.replace("&nbsp;", " ").replace("&#176;", "°")
    return re.sub(r"\s+", " ", texto).strip()


def _fecha_iso(texto_fecha):
    m = FECHA_RE.search(texto_fecha or "")
    if not m:
        return ""
    dia, mes_txt, anio = m.groups()
    mes = MESES.get(mes_txt.lower())
    if not mes:
        return ""
    try:
        return datetime(int(anio), mes, int(dia), tzinfo=timezone.utc).isoformat()
    except ValueError:
        return ""


def obtener_licitaciones():
    """Devuelve (licitaciones, error), mismo formato que las demás fuentes."""
    req = Request(URL, headers={"User-Agent": "GECC-Monitor-Licitaciones/1.0"})
    try:
        with urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except (URLError, HTTPError, TimeoutError) as e:
        return [], f"Error al consultar el portal de San Pedro Garza García: {e}"

    licitaciones = []
    bloques = html.split("<div class='accordion-container'>")[1:]
    for bloque in bloques:
        conv_m = CONVOCATORIA_RE.search(bloque)
        if not conv_m:
            continue  # todavía en planeación, sin convocatoria publicada

        titulo_m = TITULO_RE.search(bloque)
        titulo = _limpiar_texto(titulo_m.group(1)) if titulo_m else ""
        if not titulo:
            continue

        numero_m = NUMERO_RE.search(bloque)
        numero = numero_m.group(1) if numero_m else ""

        desc_m = DESC_RE.search(bloque)
        tipo_m = TIPO_RE.search(bloque)
        descripcion = " ".join(
            _limpiar_texto(m.group(1)) for m in (tipo_m, desc_m) if m
        )

        solicitante_m = SOLICITANTE_RE.search(bloque)
        comprador = _limpiar_texto(solicitante_m.group(1)) if solicitante_m else ""

        fecha_texto, link_relativo = conv_m.groups()
        identificador = numero.replace("/", "-") if numero else _limpiar_texto(titulo)[:60]

        licitaciones.append({
            "ocid": f"sanpedro-{identificador}",
            "titulo": titulo,
            "descripcion": descripcion,
            "comprador": comprador or "Municipio de San Pedro Garza García",
            "ubicacion": UBICACION,
            "fecha_publicacion": _fecha_iso(fecha_texto),
            "fecha_limite": "",
            "link": urljoin(URL, link_relativo),
            "fuente": FUENTE,
        })
    return licitaciones, None
