# -*- coding: utf-8 -*-
"""
main.py — Orquestador del monitor de licitaciones GECC.

Qué hace cada corrida:
1. Descarga licitaciones recientes de tres fuentes: la API oficial de
   Contrataciones Abiertas del Gobierno de México (api.datos.gob.mx), el
   portal de Obra Pública del Estado de Guanajuato y el portal de
   Convocatorias y Licitaciones del Municipio de León (ver scripts/fuentes/).
2. Clasifica cada una contra las categorías de negocio de GECC leyendo el
   texto completo (no solo una palabra exacta), usando keywords.clasificar
   para las tres fuentes por igual.
3. Compara contra lo ya detectado en corridas anteriores (data/licitaciones.json)
   para no duplicar, sin importar de qué fuente venga.
4. Guarda el resultado actualizado.
5. Llama a build_site.py para regenerar la página HTML.

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
from fuentes import guanajuato_estatal, leon  # noqa: E402

API_BASE = "https://api.datos.gob.mx/v2/contratacionesabiertas"
PAGE_SIZE = 200
MAX_PAGES_PER_RUN = 15  # tope de seguridad para no tardar horas ni saturar la API
REQUEST_TIMEOUT = 30
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
LICITACIONES_PATH = os.path.join(DATA_DIR, "licitaciones.json")
LOG_PATH = os.path.join(DATA_DIR, "run_log.json")


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

    # Fuente 2: Obra Pública del Estado de Guanajuato
    candidatos_gto, error_gto = guanajuato_estatal.obtener_licitaciones()
    if error_gto:
        log_run(error_gto, "error")
    agregadas_gto = procesar_candidatos(candidatos_gto, ocids_vistos, nuevas)

    # Fuente 3: Convocatorias y Licitaciones del Municipio de León
    candidatos_leon, error_leon = leon.obtener_licitaciones()
    if error_leon:
        log_run(error_leon, "error")
    agregadas_leon = procesar_candidatos(candidatos_leon, ocids_vistos, nuevas)

    existentes["licitaciones"] = nuevas + existentes["licitaciones"]
    existentes["ultima_actualizacion"] = datetime.now(timezone.utc).isoformat()

    guardar(existentes)
    log_run(
        "Corrida completada. Nuevas licitaciones relevantes: "
        f"{agregadas_federal} federal, {agregadas_gto} Guanajuato estatal, {agregadas_leon} León."
    )
    print(
        f"Listo. {len(nuevas)} licitaciones nuevas relevantes agregadas "
        f"(federal: {agregadas_federal}, Guanajuato estatal: {agregadas_gto}, León: {agregadas_leon})."
    )


if __name__ == "__main__":
    main()
