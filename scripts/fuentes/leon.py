# -*- coding: utf-8 -*-
"""
leon.py — Fuente: Convocatorias y Licitaciones del Municipio de León, Gto.

La página https://leon.gob.mx/convocatorias-licitaciones.php carga la
tabla con un $.ajax() de jQuery, pero el endpoint que llama
(modulos/licitaciones/ajax_licitaciones_teso-v2.php) regresa un fragmento
de HTML con la tabla ya armada en el servidor — no requiere navegador,
solo replicar la misma petición POST.

La tabla no trae columnas separadas de fecha de publicación ni fecha
límite: la fecha límite de presentación de propuestas va escrita dentro
del párrafo de la columna "Acto apertura de propuestas técnicas y
económicas" (ej. "...PRESENTARLAS EL DÍA 7 DE AGOSTO DE 2026 HASTA LAS
09:00 HORAS..."), así que se extrae con una expresión regular. No hay
fecha de publicación expuesta en ningún lado de la respuesta, así que
'fecha_publicacion' se deja vacía.
"""

import hashlib
import re
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ENDPOINT = "https://leon.gob.mx/modulos/licitaciones/ajax_licitaciones_teso-v2.php"
REQUEST_TIMEOUT = 30
MAX_PAGINAS = 10  # ~50 licitaciones más recientes por corrida (el listado viene ordenado de más nueva a más vieja); de sobra para detectar lo nuevo cada 2 horas sin saturar el sitio del municipio
FUENTE = "Convocatorias y Licitaciones — Municipio de León"
COMPRADOR = "Municipio de León, Guanajuato"
UBICACION = "Guanajuato"

FILA_RE = re.compile(r"<tr>\s*(.*?)\s*</tr>", re.DOTALL)
CELDA_RE = re.compile(r"<td[^>]*>(.*?)</td>", re.DOTALL)
ENLACE_RE = re.compile(r"href='([^']+\.pdf)'", re.IGNORECASE)
TAG_RE = re.compile(r"<[^>]+>")

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11,
    "diciembre": 12,
}
FECHA_LIMITE_RE = re.compile(
    r"D[IÍ]A\s+(\d{1,2})\s+DE\s+([A-ZÁÉÍÓÚ]+)\s+DE\s+(\d{4})\s+HASTA\s+LAS\s+(\d{1,2}):(\d{2})",
    re.IGNORECASE,
)


def _quitar_tags(html_fragmento):
    return TAG_RE.sub(" ", html_fragmento).strip()


def _extraer_fecha_limite(texto_apertura):
    m = FECHA_LIMITE_RE.search(texto_apertura.upper())
    if not m:
        return ""
    dia, mes_txt, anio, hora, minuto = m.groups()
    mes = MESES.get(mes_txt.lower())
    if not mes:
        return ""
    try:
        dt = datetime(int(anio), mes, int(dia), int(hora), int(minuto), tzinfo=timezone.utc)
        return dt.isoformat()
    except ValueError:
        return ""


def _fetch_pagina(pagina, filtro=""):
    body = urlencode({"filtro": filtro, "formulario": 1, "pagina": pagina}).encode("utf-8")
    req = Request(
        ENDPOINT,
        data=body,
        headers={
            "User-Agent": "GECC-Monitor-Licitaciones/1.0",
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Requested-With": "XMLHttpRequest",
        },
        method="POST",
    )
    with urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
        return resp.read().decode("utf-8", errors="replace")


def obtener_licitaciones():
    """
    Devuelve (licitaciones, error), mismo formato que las demás fuentes.
    Recorre solo las primeras MAX_PAGINAS páginas del listado (las más
    recientes), para no sobrecargar el sitio del municipio en cada corrida.
    """
    licitaciones = []
    try:
        for pagina in range(1, MAX_PAGINAS + 1):
            html = _fetch_pagina(pagina)
            filas = FILA_RE.findall(html)
            if not filas:
                break
            for fila in filas:
                celdas = CELDA_RE.findall(fila)
                if len(celdas) < 4:
                    continue
                clave = _quitar_tags(celdas[0])
                titulo = _quitar_tags(celdas[1])
                if not clave and not titulo:
                    continue
                enlace_match = ENLACE_RE.search(celdas[2])
                link = enlace_match.group(1) if enlace_match else ""
                texto_apertura = _quitar_tags(celdas[3])

                identificador = clave or hashlib.md5(
                    (titulo + link).encode("utf-8")
                ).hexdigest()[:12]

                licitaciones.append({
                    "ocid": f"leon-{identificador}",
                    "titulo": titulo,
                    "descripcion": texto_apertura[:500],
                    "comprador": COMPRADOR,
                    "ubicacion": UBICACION,
                    "fecha_publicacion": "",
                    "fecha_limite": _extraer_fecha_limite(texto_apertura),
                    "link": link,
                    "fuente": FUENTE,
                })
    except (URLError, HTTPError, TimeoutError) as e:
        return licitaciones, (
            f"Error al consultar el portal de León (parcial: "
            f"{len(licitaciones)} obtenidas antes del error): {e}"
        )
    return licitaciones, None
