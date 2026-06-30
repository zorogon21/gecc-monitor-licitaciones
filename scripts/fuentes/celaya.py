# -*- coding: utf-8 -*-
"""
celaya.py — Fuente: Licitaciones y Convocatorias de la Presidencia Municipal
de Celaya, Gto.

https://www.celaya.gob.mx/consulta/licitaciones/ y
https://www.celaya.gob.mx/consulta/convocatorias/ son páginas de archivo de
WordPress (cada licitación/convocatoria es un post normal de WP), generadas
en el servidor — no requieren navegador.

La fecha de publicación se muestra en el listado como texto en español
("junio 26, 2026"), así que se convierte con un diccionario de meses. No
hay una fecha límite visible ni en el listado ni en el cuerpo del post (las
bases completas solo están en el PDF adjunto), así que 'fecha_limite' se
deja vacía.
"""

import re
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE = "https://www.celaya.gob.mx/consulta"
CATEGORIAS = ["licitaciones", "convocatorias"]
MAX_PAGINAS_POR_CATEGORIA = 3  # ~30 más recientes por categoría; de sobra para detectar lo nuevo cada 2 horas
REQUEST_TIMEOUT = 30
FUENTE = "Licitaciones y Convocatorias — Presidencia Municipal de Celaya"
COMPRADOR = "Municipio de Celaya, Guanajuato"
UBICACION = "Guanajuato"

ARTICULO_RE = re.compile(r"<article.*?</article>", re.DOTALL)
TITULO_RE = re.compile(
    r'bt_bb_headline_content"><span><a href="([^"]+)"[^>]*title="([^"]+)"',
)
FECHA_RE = re.compile(r'asgItem date"><small>([^<]+)</small>')

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11,
    "diciembre": 12,
}
FECHA_PROSA_RE = re.compile(r"([a-záéíóú]+)\s+(\d{1,2}),\s*(\d{4})", re.IGNORECASE)


def _fecha_iso(texto_fecha):
    """Convierte 'junio 26, 2026' a ISO 8601. Regresa '' si no se pudo."""
    m = FECHA_PROSA_RE.search(texto_fecha or "")
    if not m:
        return ""
    mes_txt, dia, anio = m.groups()
    mes = MESES.get(mes_txt.lower())
    if not mes:
        return ""
    try:
        return datetime(int(anio), mes, int(dia), tzinfo=timezone.utc).isoformat()
    except ValueError:
        return ""


def _fetch(url):
    req = Request(url, headers={"User-Agent": "GECC-Monitor-Licitaciones/1.0"})
    with urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
        return resp.read().decode("utf-8", errors="replace")


def obtener_licitaciones():
    """
    Devuelve (licitaciones, error). Recorre las primeras
    MAX_PAGINAS_POR_CATEGORIA páginas de cada categoría (licitaciones y
    convocatorias), que vienen ordenadas de la más nueva a la más vieja.
    """
    licitaciones = []
    vistos = set()
    try:
        for categoria in CATEGORIAS:
            for pagina in range(1, MAX_PAGINAS_POR_CATEGORIA + 1):
                url = f"{BASE}/{categoria}/" if pagina == 1 else f"{BASE}/{categoria}/page/{pagina}/"
                try:
                    html = _fetch(url)
                except HTTPError as e:
                    if e.code == 404:
                        break  # no hay más páginas en esta categoría
                    raise

                articulos = ARTICULO_RE.findall(html)
                if not articulos:
                    break

                for art in articulos:
                    m = TITULO_RE.search(art)
                    if not m:
                        continue
                    link, titulo = m.group(1), m.group(2)
                    if link in vistos:
                        continue
                    vistos.add(link)

                    fecha_m = FECHA_RE.search(art)
                    fecha_publicacion = _fecha_iso(fecha_m.group(1)) if fecha_m else ""

                    licitaciones.append({
                        "ocid": f"celaya-{link.rstrip('/').rsplit('/', 1)[-1]}",
                        "titulo": titulo.strip(),
                        "descripcion": "",
                        "comprador": COMPRADOR,
                        "ubicacion": UBICACION,
                        "fecha_publicacion": fecha_publicacion,
                        "fecha_limite": "",
                        "link": link,
                        "fuente": FUENTE,
                    })
    except (URLError, HTTPError, TimeoutError) as e:
        return licitaciones, (
            f"Error al consultar el portal de Celaya (parcial: "
            f"{len(licitaciones)} obtenidas antes del error): {e}"
        )
    return licitaciones, None
