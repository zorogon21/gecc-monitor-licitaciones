# -*- coding: utf-8 -*-
"""
main.py — Orquestador del monitor de licitaciones GECC.

Qué hace cada corrida:
1. Descarga licitaciones recientes de la API oficial de Contrataciones
   Abiertas del Gobierno de México (api.datos.gob.mx) y de cada fuente
   municipal/estatal en scripts/fuentes/ (ver FUENTES_SIMPLES más abajo).
2. Clasifica cada una contra las categorías de negocio de GECC leyendo el
   texto completo (no solo una palabra exacta), usando keywords.clasificar
   para todas las fuentes por igual.
3. Compara contra lo ya detectado en corridas anteriores (data/licitaciones.json)
   para no duplicar, sin importar de qué fuente venga.
4. Descarta licitaciones vencidas (filtrar_vigentes), tanto de lo nuevo
   como de lo ya guardado.
5. Guarda el resultado actualizado.
6. Llama a build_site.py para regenerar la página HTML.

Diseñado para correr cada 2 horas vía GitHub Actions (ver
.github/workflows/monitor.yml). Si una fuente cambia de forma o un campo no
existe, el script no debe tronar — debe registrar el problema en
data/run_log.json y seguir con las demás fuentes que sí pudo procesar.
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

sys.path.insert(0, os.path.dirname(__file__))
from keywords import clasificar  # noqa: E402
from fuentes import (  # noqa: E402
    apaseo_el_grande,
    celaya,
    guanajuato_capital,
    guanajuato_estatal,
    leon,
    salamanca,
    uriangato,
)

# Fuentes que solo necesitan llamar a obtener_licitaciones() (a diferencia
# de la API federal, que pagina con su propio ciclo más abajo). Cada
# elemento es (nombre para mostrar en logs, módulo de scripts/fuentes/).
FUENTES_SIMPLES = [
    ("Guanajuato estatal", guanajuato_estatal),
    ("León", leon),
    ("Celaya", celaya),
    ("Apaseo el Grande", apaseo_el_grande),
    ("Salamanca", salamanca),
    ("Guanajuato capital", guanajuato_capital),
    ("Uriangato", uriangato),
]

API_BASE = "https://api.datos.gob.mx/v2/contratacionesabiertas"
PAGE_SIZE = 200
MAX_PAGES_PER_RUN = 15  # tope de seguridad para no tardar horas ni saturar la API
REQUEST_TIMEOUT = 30
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
LICITACIONES_PATH = os.path.join(DATA_DIR, "licitaciones.json")
LOG_PATH = os.path.join(DATA_DIR, "run_log.json")

# Si una licitación no trae fecha límite (p.ej. el portal estatal de
# Guanajuato, que solo da PDFs por etapa), se asume vencida cuando su fecha
# de publicación tiene más de esta cantidad de días.
DIAS_MAX_SIN_FECHA_LIMITE = 60


def fetch_pagina(page):
    url = f"{API_BASE}?pageSize={PAGE_SIZE}&page={page}"
    req = Request(url, headers={"User-Agent": "GECC-Monitor-Licitaciones/1.0"})
    try:
        with urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            raw = resp.read()
            return json.loads(raw)
    except (URLError, HTTPError, TimeoutError, json.JSONDecodeError) as e:
        return {"_error": str(e)}


def extraer_campos(record):
    """
    Extrae los campos relevantes de un 'record' OCDS. La estructura puede
    variar; se navega de forma defensiva y se regresa None si no hay datos
    mínimos utilizables.
    """
    try:
        releases = record.get("releases") or []
        if not releases:
            return None
        release = releases[-1]  # el más reciente del expediente
        tender = release.get("tender") or {}
        buyer = release.get("buyer") or {}
        parties = release.get("parties") or []

        titulo = tender.get("title") or ""
        descripcion = tender.get("description") or ""
        ocid = record.get("ocid") or release.get("ocid") or ""

        # Intentar ubicar la entidad/estado del comprador entre las "parties"
        ubicacion = ""
        for p in parties:
            if p.get("id") == buyer.get("id") or "buyer" in (p.get("roles") or []):
                direccion = (p.get("address") or {})
                ubicacion = direccion.get("region") or direccion.get("locality") or ""
                if ubicacion:
                    break

        fecha_publicacion = tender.get("tenderPeriod", {}).get("startDate") or release.get("date") or ""
        fecha_limite = tender.get("tenderPeriod", {}).get("endDate") or ""

        link = ""
        docs = tender.get("documents") or []
        if docs:
            link = docs[0].get("url", "")
        if not link:
            link = release.get("uri") or ""

        return {
            "ocid": ocid,
            "titulo": titulo.strip(),
            "descripcion": descripcion.strip(),
            "comprador": buyer.get("name", "").strip(),
            "ubicacion": ubicacion.strip(),
            "fecha_publicacion": fecha_publicacion,
            "fecha_limite": fecha_limite,
            "link": link,
            "fuente": "Contrataciones Abiertas (Gobierno Federal)",
        }
    except Exception:
        return None


def cargar_existentes():
    if os.path.exists(LICITACIONES_PATH):
        with open(LICITACIONES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"licitaciones": [], "ultima_actualizacion": None}


def guardar(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(LICITACIONES_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def log_run(mensaje, nivel="info"):
    os.makedirs(DATA_DIR, exist_ok=True)
    entradas = []
    if os.path.exists(LOG_PATH):
        try:
            with open(LOG_PATH, "r", encoding="utf-8") as f:
                entradas = json.load(f)
        except Exception:
            entradas = []
    entradas.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "nivel": nivel,
        "mensaje": mensaje,
    })
    entradas = entradas[-200:]  # no dejar crecer el log indefinidamente
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(entradas, f, ensure_ascii=False, indent=2)


def _parsear_fecha(fecha_str):
    """
    Intenta interpretar una fecha en formato ISO 8601 (con o sin 'Z', con o
    sin hora). Regresa un datetime con tzinfo en UTC, o None si el valor
    está vacío o no se pudo interpretar.
    """
    if not fecha_str or not isinstance(fecha_str, str):
        return None
    try:
        dt = datetime.fromisoformat(fecha_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def filtrar_vigentes(licitaciones, ahora=None):
    """
    Descarta licitaciones vencidas, sin importar de qué fuente vengan:
    - Si tienen 'fecha_limite' y ya pasó respecto a 'ahora', se excluyen.
    - Si NO tienen 'fecha_limite' interpretable pero sí 'fecha_publicacion',
      y esta tiene más de DIAS_MAX_SIN_FECHA_LIMITE días de antigüedad, se
      excluyen (es muy probable que ya hayan cerrado su periodo de
      propuestas aunque no tengamos la fecha límite exacta).
    - Si no hay ninguna fecha interpretable, se conserva: no se descarta
      por falta de información.
    Se usa tanto sobre licitaciones recién detectadas como sobre las que ya
    estaban guardadas, para que data/licitaciones.json se vaya podando solo
    con el tiempo en lugar de crecer indefinidamente.
    """
    if ahora is None:
        ahora = datetime.now(timezone.utc)

    vigentes = []
    for lic in licitaciones:
        fecha_limite = _parsear_fecha(lic.get("fecha_limite"))
        if fecha_limite is not None:
            if fecha_limite < ahora:
                continue  # vencida: ya pasó su fecha límite
            vigentes.append(lic)
            continue

        fecha_publicacion = _parsear_fecha(lic.get("fecha_publicacion"))
        if fecha_publicacion is not None and (ahora - fecha_publicacion).days > DIAS_MAX_SIN_FECHA_LIMITE:
            continue  # sin fecha límite, pero publicada hace demasiado tiempo

        vigentes.append(lic)

    return vigentes


def procesar_candidatos(candidatos, ocids_vistos, nuevas):
    """
    Aplica deduplicación (contra lo ya visto en esta corrida o en corridas
    anteriores) y clasificación por categoría de negocio a una lista de
    licitaciones ya extraídas de cualquier fuente. Las relevantes y nuevas
    se agregan a 'nuevas'. Regresa cuántas se agregaron.
    """
    agregadas = 0
    for campos in candidatos:
        if not campos.get("ocid"):
            continue
        if campos["ocid"] in ocids_vistos:
            continue
        ocids_vistos.add(campos["ocid"])

        texto_completo = f"{campos.get('titulo', '')} {campos.get('descripcion', '')} {campos.get('comprador', '')}"
        categorias = clasificar(texto_completo)
        if not categorias:
            continue  # no relevante para el negocio de GECC

        campos["categorias"] = categorias
        campos["detectado_en"] = datetime.now(timezone.utc).isoformat()
        nuevas.append(campos)
        agregadas += 1
    return agregadas


def main():
    existentes = cargar_existentes()
    ocids_vistos = {l["ocid"] for l in existentes["licitaciones"] if l.get("ocid")}

    nuevas = []

    # Fuente 1: Contrataciones Abiertas (API federal)
    candidatos_federal = []
    errores_paginas = 0
    for page in range(1, MAX_PAGES_PER_RUN + 1):
        resultado = fetch_pagina(page)
        if "_error" in resultado:
            errores_paginas += 1
            log_run(f"Error al descargar página {page} (federal): {resultado['_error']}", "error")
            if errores_paginas >= 3:
                break
            continue

        records = resultado.get("results") or resultado.get("records") or []
        if not records:
            break  # se acabaron las páginas

        for record in records:
            campos = extraer_campos(record)
            if campos:
                candidatos_federal.append(campos)

        time.sleep(0.5)  # ser cordial con la API del gobierno
    agregadas_federal = procesar_candidatos(candidatos_federal, ocids_vistos, nuevas)

    resumen_fuentes = [f"{agregadas_federal} federal"]
    for nombre, modulo in FUENTES_SIMPLES:
        candidatos, error = modulo.obtener_licitaciones()
        if error:
            log_run(error, "error")
        agregadas = procesar_candidatos(candidatos, ocids_vistos, nuevas)
        resumen_fuentes.append(f"{agregadas} {nombre}")

    todas = nuevas + existentes["licitaciones"]
    total_antes_de_podar = len(todas)
    vigentes = filtrar_vigentes(todas)
    podadas = total_antes_de_podar - len(vigentes)

    existentes["licitaciones"] = vigentes
    existentes["ultima_actualizacion"] = datetime.now(timezone.utc).isoformat()

    guardar(existentes)
    detalle = ", ".join(resumen_fuentes)
    log_run(
        f"Corrida completada. Nuevas licitaciones relevantes: {detalle}. "
        f"Vencidas podadas: {podadas}."
    )
    print(
        f"Listo. {len(nuevas)} licitaciones nuevas relevantes agregadas ({detalle}). "
        f"{podadas} licitaciones vencidas podadas del archivo."
    )


if __name__ == "__main__":
    main()
