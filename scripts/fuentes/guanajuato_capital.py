# -*- coding: utf-8 -*-
"""
guanajuato_capital.py — Fuente: Licitaciones y Convocatorias del Municipio
de Guanajuato (capital), Gto.

https://www.guanajuatocapital.gob.mx/cat_doc/licitaciones-publicas-adquisiciones/
y /cat_doc/convocatorias-publicas/ son páginas de archivo de WordPress
(custom post type "ova_doc") con título y link a cada documento, pero sin
fecha visible en el listado. La API REST de WordPress no expone ese custom
post type, así que no hay atajo: hay que entrar a cada página de detalle
para sacar el PDF correcto (el sitio mete un sidebar genérico con decenas
de PDFs no relacionados, así que se aísla el de la sección
"ova-list-attachment", que es el específico del documento) y se infiere la
fecha de publicación de la carpeta año/mes de la URL del PDF (no hay fecha
explícita en ningún lado). Por eso solo se recorre la página más reciente
de cada categoría — ya implica una petición HTTP por documento.
"""

import re
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE = "https://www.guanajuatocapital.gob.mx/cat_doc"
CATEGORIAS = ["licitaciones-publicas-adquisiciones", "convocatorias-publicas"]
REQUEST_TIMEOUT = 30
FUENTE = "Licitaciones y Convocatorias — Municipio de Guanajuato (capital)"
COMPRADOR = "Municipio de Guanajuato"
UBICACION = "Guanajuato"

ENLACE_DOC_RE = re.compile(
    r'<a[^>]+href="(https://www\.guanajuatocapital\.gob\.mx/ova_doc/[^"]+)"[^>]*>([^<]*)</a>'
)
ADJUNTO_RE = re.compile(r'ova-list-attachment">(.*?)</ul>', re.DOTALL)
PDF_RE = re.compile(r'href="([^"]+\.pdf)"', re.IGNORECASE)
ANIO_MES_RE = re.compile(r"/wp-content/uploads/(\d{4})/(\d{2})/")


def _fetch(url):
    req = Request(url, headers={"User-Agent": "GECC-Monitor-Licitaciones/1.0"})
    with urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _extraer_detalle(url_detalle):
    """Regresa (link_pdf, fecha_publicacion) leyendo la página de detalle."""
    html = _fetch(url_detalle)
    m = ADJUNTO_RE.search(html)
    if not m:
        return "", ""
    pdf_m = PDF_RE.search(m.group(1))
    if not pdf_m:
        return "", ""
    link_pdf = pdf_m.group(1)
    fecha_m = ANIO_MES_RE.search(link_pdf)
    fecha_publicacion = f"{fecha_m.group(1)}-{fecha_m.group(2)}-01T00:00:00Z" if fecha_m else ""
    return link_pdf, fecha_publicacion


def obtener_licitaciones():
    """Devuelve (licitaciones, error), mismo formato que las demás fuentes."""
    candidatos = []  # (titulo, url_detalle)
    vistos = set()
    try:
        for categoria in CATEGORIAS:
            html = _fetch(f"{BASE}/{categoria}/")
            for url_detalle, titulo in ENLACE_DOC_RE.findall(html):
                if url_detalle in vistos or not titulo.strip():
                    continue
                vistos.add(url_detalle)
                candidatos.append((titulo.strip(), url_detalle))
    except (URLError, HTTPError, TimeoutError) as e:
        return [], f"Error al consultar el archivo de Guanajuato capital: {e}"

    licitaciones = []
    for titulo, url_detalle in candidatos:
        try:
            link_pdf, fecha_publicacion = _extraer_detalle(url_detalle)
        except (URLError, HTTPError, TimeoutError):
            link_pdf, fecha_publicacion = "", ""
        slug = url_detalle.rstrip("/").rsplit("/", 1)[-1]
        licitaciones.append({
            "ocid": f"gtocap-{slug}",
            "titulo": titulo,
            "descripcion": "",
            "comprador": COMPRADOR,
            "ubicacion": UBICACION,
            "fecha_publicacion": fecha_publicacion,
            "fecha_limite": "",
            "link": link_pdf or url_detalle,
            "fuente": FUENTE,
        })
        time.sleep(0.3)  # ser cordial: esto implica una petición HTTP extra por documento

    return licitaciones, None
