#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json
import os
import hashlib
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse

# ============================================================
# Força que el JSON es creï al costat del script, encara amb cron
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_FILE = os.path.join(BASE_DIR, "ofertas_sociologia.json")

# ============================================================
# Configuració de contacte i headers per scraping ètic
# ============================================================
CONTACT_EMAIL = ""
HEADERS = {
    "User-Agent": f"OfertesUniScraper (contact: {CONTACT_EMAIL})"
}

# ============================================================
# Paràmetres globals per a les dues fonts
# ============================================================
API_URL = (
    "https://tauler.seu-e.cat/api/edictes?"
    "page=0&size=25&sort=dataPublicacioEfectiva%2Cdesc&ens=11&locale=ca"
)
BASE_ENLACE_EDICTES = "https://tauler.seu-e.cat/detall?idEns=11&idEdicte="
FILTER_CLASSIFICATION = "Selecció de PAS"
FILTER_TITLE_KEYWORDS = ["sociologia", "polítiques"]
MAX_DAYS_API = 3  # només edictes publicats fa menys de 3 dies

SCRAP_URL_BASE = (
    "https://seu.ub.edu/ofertaPublicaCategoriaPublic/categories?"
    "tipus=totes&text=sociologia&estat=Oberta&tipusOferta=59158&"
    "dataOfertaPublicaFilter=dataPublicacio&ordreOfertaPublicaFilter=desc.label"
)
SCRAP_FILTER_PHRASES = ["sociologia", "polítiques"]
MAX_DAYS_SCRAP = 30
MAX_RESULT_SCRAP = 100

#Escriu aqui el Telegram_Bot_token i Telegram_Chat_id
TELEGRAM_BOT_TOKEN = ""
TELEGRAM_CHAT_ID = ""

# ============================================================
# Funcions auxiliars
# ============================================================
def extraer_id_seguiment(titulo: str) -> str:
    """Retorna la primera ‘palabra’ del títol (fins al primer espai)."""
    return titulo.split()[0] if titulo else ""


def generar_id_numeric(titulo: str) -> str:
    """SHA-256 dels 10 primers caràcters i extracció de 10 dígits."""
    partial = titulo[:10]
    h = hashlib.sha256(partial.encode()).hexdigest()
    return str(int(h, 16))[:10]


def get_edictes() -> list:
    """Obté i filtra edictes de la UAB via API."""
    resp = requests.get(API_URL, headers=HEADERS)
    resp.raise_for_status()
    data = resp.json().get("edictes", [])
    resultados = []
    now = datetime.now()

    for edicte in data:
        titulo = edicte.get("titol", "")
        # filtrar classificació PAS
        cls = next(
            (c for c in edicte.get("classificacions", [])
             if c.get("subcategoria") == FILTER_CLASSIFICATION),
            None
        )
        if not cls:
            continue

        # filtrar paraules clau al títol
        if not any(k.lower() in titulo.lower() for k in FILTER_TITLE_KEYWORDS):
            continue

        # filtrar data
        try:
            pub = datetime.strptime(edicte.get("data_publicacio", ""), "%Y-%m-%d")
        except ValueError:
            continue
        if (now - pub).days >= MAX_DAYS_API:
            continue

        resultados.append({
            "titulo": titulo,
            "fecha_publicacion": pub.strftime("%Y-%m-%d"),
            "estado": edicte.get("tags", [""])[0],
            "enlace": BASE_ENLACE_EDICTES + str(edicte.get("id_edicte", "")),
            "concepte": cls.get("concepte", ""),
            "categoria": cls.get("categoria", ""),
            "subcategoria": cls.get("subcategoria", ""),
            "seguiment": False,
            "universitat": "UAB"
        })

    return resultados


def scrap_ofertas_filtradas(url: str, filtro_frases=SCRAP_FILTER_PHRASES,
                            dias_maximo=MAX_DAYS_SCRAP) -> list:
    """Scraping d'ofertes de la UB i filtrar per títol, estat i data."""
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    rows = soup.find_all("tr")
    avui = datetime.now().date()
    data_limit = avui - timedelta(days=dias_maximo)
    llista = []

    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 4:
            continue

        a = row.find("a")
        if a:
            titulo = a.get_text(strip=True)
            enlace = urljoin(url, a["href"])
        else:
            titulo = row.get_text(strip=True)
            enlace = ""

        try:
            pub_str = cols[1].get_text(strip=True)
            pub_date = datetime.strptime(pub_str, "%d-%m-%Y").date()
        except ValueError:
            continue

        estat = cols[3].get_text(strip=True)
        if estat.lower() != "oberta":
            continue

        if not any(k.lower() in titulo.lower() for k in filtro_frases):
            continue

        if not (data_limit <= pub_date <= avui):
            continue

        llista.append({
            "titulo": titulo,
            "fecha_publicacion": pub_date.strftime("%Y-%m-%d"),
            "estado": estat,
            "enlace": enlace,
            "concepte": "",
            "categoria": "",
            "subcategoria": "",
            "seguiment": False,
            "universitat": "UB"
        })

    return llista


def construir_url_con_paginacion(base: str, max_r: int, offset: int) -> str:
    parts = list(urlparse(base))
    q = parse_qs(parts[4])
    q["max"] = [str(max_r)]
    q["offset"] = [str(offset)]
    parts[4] = urlencode(q, doseq=True)
    return urlunparse(parts)


def scrap_totes_ofertes(url_base: str) -> list:
    """Recorre pàgines de la UB amb paginació."""
    totes = []
    offset = 0
    while True:
        pag = construir_url_con_paginacion(url_base, MAX_RESULT_SCRAP, offset)
        print(f"Procesant: {pag}")
        ofertes = scrap_ofertas_filtradas(pag)
        if not ofertes:
            break
        totes.extend(ofertes)
        if len(ofertes) < MAX_RESULT_SCRAP:
            break
        offset += MAX_RESULT_SCRAP
    return totes


def detectar_ofertes(current_offers: list, archivo_json: str):
    """
    1) Carrega l’històric existents.
    2) Afegeix noves i detecta actualitzacions per seguiment.
    3) Escriu de nou TOT l’històric acumulat.
    """
    # --- 1. històric
    if os.path.exists(archivo_json):
        with open(archivo_json, "r", encoding="utf-8") as f:
            prev = json.load(f)
        prev_dict = {o["enlace"]: o for o in prev if "enlace" in o}
    else:
        prev_dict = {}

    tracked_ids = {
        extraer_id_seguiment(o["titulo"])
        for o in prev_dict.values()
        if o.get("seguiment")
    }

    noves, updates = [], []

    # --- 2. comparar
    for o in current_offers:
        uni = o.get("universitat")
        cond_uab = (
            uni == "UAB"
            and o.get("concepte") == "Tipus de documents"
            and o.get("categoria") == "Convocatòria"
            and o.get("subcategoria") == "Selecció de PAS"
        )
        cond_ub = uni == "UB"
        if not (cond_uab or cond_ub):
            continue

        enlace = o["enlace"]
        seg = extraer_id_seguiment(o["titulo"])

        # nova?
        if enlace not in prev_dict:
            prev_dict[enlace] = o
            if seg in tracked_ids:
                updates.append(o)
            else:
                noves.append(o)
        # si ja existia, no fem res (informació ja registrada)

    # --- 3. escriure l’històric
    with open(archivo_json, "w", encoding="utf-8") as f:
        json.dump(list(prev_dict.values()), f, ensure_ascii=False, indent=4)

    return noves, updates


def send_telegram_message(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    resp = requests.post(url, json=payload, headers=HEADERS)
    resp.raise_for_status()


def generar_missatge(o: dict) -> str:
    seg = o.get("idSeguiment") or extraer_id_seguiment(o["titulo"])
    return (
        f"• Títol: {o['titulo']}\n"
        f"• Data Publicació: {o['fecha_publicacion']}\n"
        f"• Estat: {o['estado']}\n"
        f"• Enllaç: {o['enlace']}\n"
        f"• idSeguiment: {seg}\n"
        f"• Seguiment: {o['seguiment']}\n"
        f"• Universitat: {o['universitat']}\n"
    )


def process_telegram_commands():
    """Llegeix /seguiment des de Telegram i actualitza el JSON."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    try:
        resp = requests.get(url, headers=HEADERS)
        resp.raise_for_status()
    except Exception as e:
        print("Error Telegram getUpdates:", e)
        return

    updates = resp.json().get("result", [])
    # carregar guardades
    if os.path.exists(JSON_FILE):
        with open(JSON_FILE, "r", encoding="utf-8") as f:
            guardades = json.load(f)
    else:
        guardades = []

    changed = False
    for upd in updates:
        txt = upd.get("message", {}).get("text", "")
        if txt.startswith("/seguiment"):
            parts = txt.split()
            if len(parts) >= 2:
                idseg = parts[1]
                for o in guardades:
                    seg_actual = o.get("idSeguiment") or extraer_id_seguiment(o["titulo"])
                    if seg_actual == idseg and not o.get("seguiment"):
                        o["seguiment"] = True
                        o["idSeguiment"] = idseg  # es guarda només ara
                        send_telegram_message(f"Seguiment activat per idSeguiment {idseg}")
                        changed = True
                        break
                else:
                    send_telegram_message(f"No s'ha trobat oferta amb idSeguiment {idseg}")

    if changed:
        with open(JSON_FILE, "w", encoding="utf-8") as f:
            json.dump(guardades, f, ensure_ascii=False, indent=4)


def main():
    process_telegram_commands()

    eds = get_edictes()
    scraps = scrap_totes_ofertes(SCRAP_URL_BASE)
    all_offers = eds + scraps

    noves, actuals = detectar_ofertes(all_offers, JSON_FILE)

    if noves:
        msg = "===== Ofertes Noves =====\n" + "\n".join(generar_missatge(o) for o in noves)
        send_telegram_message(msg)
    else:
        send_telegram_message("No s'han detectat ofertes noves")

    if actuals:
        msg = "===== Actualitzacions =====\n" + "\n".join(generar_missatge(o) for o in actuals)
        send_telegram_message(msg)
    else:
        send_telegram_message("No s'han detectat noves actualitzacions")


if __name__ == "__main__":
    main()
