# -*- coding: utf-8 -*-
"""
irapuato.py — Fuente: Licitaciones y Concursos del Municipio de Irapuato,
Gto.

https://irapuato.gob.mx/licitaciones-y-concursos/ es HTML estático
generado por el WordPress Page Builder (no requiere navegador): cada
convocatoria es un párrafo con el texto legal de la convocatoria y un
link al PDF; el objeto de la licitación (ej. "LPN-02/2026 PRIMERA
CONVOCATORIA – ADQUISICIÓN DE FERTILIZANTE") va en el último <strong>
antes del link al PDF, no en el texto del link mismo (que es solo un
ícono de descarga).

Solo se incluyen los PDFs de "convocatoria_..." (la invitación abierta);
se descartan los de "actafallo_..." (acta de fallo: el proceso ya se
resolvió, ya no es una oportunidad abierta).

No hay fecha de publicación ni fecha límite explícitas en ningún lado
del HTML. Se usa la carpeta año/mes de la propia URL del PDF como
fecha_publicacion (mismo criterio que guanajuato_capital.py: es la fecha
real de subida del archivo, no una fecha inventada); fecha_limite se deja
vacía.
"""

import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

URL = "https://irapuato.gob.mx/licitaciones-y-concursos/"
REQUEST_TIMEOUT = 30
FUENTE = "Licitaciones y Concursos — Municipio de Irapuato"
COMPRADOR = "Municipio de Irapuato"
UBICACION = "Guanajuato"

PDF_RE = re.compile(
    r'href="(https://www\.irapuato\.gob\.mx/uploads/licitaciones_y_concursos/'
    r'(\d{4})/([a-z]+)/(convocatoria[^"/]*\.pdf))"',
    re.IGNORECASE,
)
STRONG_RE = re.compile(r"<strong>([^<]+)</strong>", re.IGNORECASE)
VENTANA_TITULO = 3000  # caracteres hacia atrás donde buscar el <strong> con el objeto

MESES = {
    "enero": "01", "febrero": "02", "marzo": "03", "abril": "04",
    "mayo": "05", "junio": "06", "julio": "07", "agosto": "08",
    "septiembre": "09", "octubre": "10", "noviembre": "11", "diciembre": "12",
}


def _titulo_previo(html, posicion):
    ventana = html[max(0, posicion - VENTANA_TITULO):posicion]
    strongs = STRONG_RE.findall(ventana)
    if not strongs:
        return ""
    texto = strongs[-1]
    texto = re.sub(r"&#8211;|&#8212;", "-", texto)
    texto = re.sub(r"&nbsp;", " ", texto)
    return re.sub(r"\s+", " ", texto).strip(" :.-")


def obtener_licitaciones():
    """Devuelve (licitaciones, error), mismo formato que las demás fuentes."""
    req = Request(URL, headers={"User-Agent": "GECC-Monitor-Licitaciones/1.0"})
    try:
        with urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except (URLError, HTTPError, TimeoutError) as e:
        return [], f"Error al consultar el portal de Irapuato: {e}"

    licitaciones = []
    vistos = set()
    for m in PDF_RE.finditer(html):
        link, anio, mes_txt, nombre_archivo = m.groups()
        if link in vistos:
            continue
        vistos.add(link)

        titulo = _titulo_previo(html, m.start())
        if not titulo:
            continue

        mes = MESES.get(mes_txt.lower())
        fecha_publicacion = f"{anio}-{mes}-01T00:00:00Z" if mes else ""

        identificador = nombre_archivo.rsplit(".", 1)[0]
        licitaciones.append({
            "ocid": f"irapuato-{identificador}",
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
