#!/usr/bin/env python3
"""
Aquest script implementa scraping ètic per detectar ofertes de convocatòries universitàries.
S'inclou un agent (mitjançant els headers HTTP) amb el correu de contacte per permetre la comunicació
amb els responsables dels sistemes, sempre que sigui necessari.
"""

import requests
import json
import uuid
import os
import hashlib
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse

# ============================================================
# Configuració de contacte i headers per scraping ètic
# ============================================================
CONTACT_EMAIL = "your_email@example.com"  # Reemplaça amb el teu correu electrònic
HEADERS = {
    "User-Agent": f"OfertesUniScraper (contact: {CONTACT_EMAIL})"
}

# ============================================================
# Paràmetres globals per a les dues fonts
# ============================================================

# Font UAB: API de edictes
API_URL = "https://tauler.seu-e.cat/api/edictes?page=0&size=25&sort=dataPublicacioEfectiva%2Cdesc&ens=11&locale=ca"
BASE_ENLACE_EDICTES = "https://tauler.seu-e.cat/detall?idEns=11&idEdicte="
FILTER_CLASSIFICATION = "Selecció de PAS"
# Ara s'utilitza una llista de paraules clau per filtrar el títol
FILTER_TITLE_KEYWORDS = ["sociologia", "polítiques"]
MAX_DAYS_API = 3  # Es consideren ofertes publicades fa menys de 3 dies

# Font UB: Scraping de ofertes
SCRAP_URL_BASE = ("https://seu.ub.edu/ofertaPublicaCategoriaPublic/categories?"
                  "tipus=totes&text=sociologia&estat=Oberta&tipusOferta=59158&"
                  "dataOfertaPublicaFilter=dataPublicacio&ordreOfertaPublicaFilter=desc.label")
# Llista de paraules clau per filtrar el títol en el scraping
SCRAP_FILTER_PHRASES = ["sociologia", "polítiques"]
MAX_DAYS_SCRAP = 30  # Ofertes dels darrers 30 dies
MAX_RESULT_SCRAP = 100  # Nombre màxim de resultats per pàgina
JSON_FILE = "ofertas_sociologia.json"  # Fitxer per emmagatzemar l'històric i detectar novetats

# Paràmetres per Telegram
TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN"  # Reemplaça amb el teu token de bot
TELEGRAM_CHAT_ID = "YOUR_CHAT_ID"      # Reemplaça amb l'ID del chat

# ============================================================
# Funció per generar idEdicte numèric a partir dels 10 primers caràcters del títol (per UB)
# ============================================================
def generar_id_numeric(titulo):
    """
    Genera un id numèric de 10 dígits a partir dels 10 primers caràcters del títol.
    S'utilitza SHA‑256 i s'extreuen els 10 primers dígits de la seva representació numèrica.
    """
    partial = titulo[:10]
    hash_val = hashlib.sha256(partial.encode()).hexdigest()
    numeric_id = str(int(hash_val, 16))[:10]
    return numeric_id

# ============================================================
# Funcions per obtenir edictes des de l'API (UAB)
# ============================================================
def get_edictes():
    response = requests.get(API_URL, headers=HEADERS)
    response.raise_for_status()
    data = response.json()
    edictes = data.get("edictes", [])
    resultados = []
    now = datetime.now()
    
    for edicte in edictes:
        id_api = edicte.get("id_edicte", "")
        titulo = edicte.get("titol", "")
        
        # Filtrar per classificació
        classificacions = edicte.get("classificacions", [])
        matching_class = next((cl for cl in classificacions if cl.get("subcategoria") == FILTER_CLASSIFICATION), None)
        if not matching_class:
            continue

        # Comprovar si el títol conté almenys una paraula clau
        if not any(keyword.lower() in titulo.lower() for keyword in FILTER_TITLE_KEYWORDS):
            continue

        # Filtrar per data de publicació (fa menys de MAX_DAYS_API dies)
        fecha_publicacion = edicte.get("data_publicacio", "")
        try:
            fecha_dt = datetime.strptime(fecha_publicacion, "%Y-%m-%d")
        except ValueError:
            continue
        if (now - fecha_dt).days >= MAX_DAYS_API:
            continue
        
        # Extreure estat, enllaç i camps de classificació
        tags = edicte.get("tags", [])
        estado = tags[0] if tags else ""
        enlace = BASE_ENLACE_EDICTES + str(id_api)
        concepte = matching_class.get("concepte", "")
        categoria = matching_class.get("categoria", "")
        subcategoria = matching_class.get("subcategoria", "")
        
        resultados.append({
            "titulo": titulo,
            "fecha_publicacion": fecha_publicacion,
            "estado": estado,
            "enlace": enlace,
            "concepte": concepte,
            "categoria": categoria,
            "subcategoria": subcategoria,
            "idEdicte": id_api,  # s'utilitza l'idEdicte real
            "seguiment": False,
            "universitat": "UAB"
        })
    return resultados

# ============================================================
# Funcions per fer scraping en la font UB
# ============================================================
def scrap_ofertas_filtradas(url, filtro_frases=SCRAP_FILTER_PHRASES, dias_maximo=MAX_DAYS_SCRAP):
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    rows = soup.find_all('tr')
    hoy = datetime.now().date()
    fecha_limite = hoy - timedelta(days=dias_maximo)
    ofertas_filtradas = []
    
    for row in rows:
        celdas = row.find_all('td')
        if len(celdas) < 4:
            continue
        
        titulo_tag = row.find('a')
        if titulo_tag:
            titulo = titulo_tag.get_text(strip=True)
            enlace = urljoin(url, titulo_tag.get('href', '').strip())
        else:
            titulo = row.get_text(strip=True)
            enlace = ""
        
        fecha_publicacion_str = celdas[1].get_text(strip=True)
        estado = celdas[3].get_text(strip=True)
        
        # Només es consideren ofertes en estat "oberta"
        if estado.lower() != "oberta":
            continue
        
        # Verificar que el títol contingui almenys una de les frases filtrants
        if not any(keyword.lower() in titulo.lower() for keyword in filtro_frases):
            continue
        
        try:
            fecha_publicacion = datetime.strptime(fecha_publicacion_str, "%d-%m-%Y").date()
        except ValueError:
            continue
        
        if fecha_limite <= fecha_publicacion <= hoy:
            idEdicte = generar_id_numeric(titulo)
            ofertas_filtradas.append({
                "titulo": titulo,
                "fecha_publicacion": fecha_publicacion_str,
                "estado": estado,
                "enlace": enlace,
                "concepte": "",
                "categoria": "",
                "subcategoria": "",
                "idEdicte": idEdicte,
                "seguiment": False,
                "universitat": "UB"
            })
    
    return ofertas_filtradas

def construir_url_con_paginacion(url_base, max_result, offset):
    url_parts = list(urlparse(url_base))
    query = parse_qs(url_parts[4])
    query["max"] = [str(max_result)]
    query["offset"] = [str(offset)]
    url_parts[4] = urlencode(query, doseq=True)
    return urlunparse(url_parts)

def scrap_totes_ofertes(url_base, filtro_frases=SCRAP_FILTER_PHRASES, dias_maximo=MAX_DAYS_SCRAP, max_result=MAX_RESULT_SCRAP):
    totes_ofertes = []
    offset = 0
    while True:
        url_paginada = construir_url_con_paginacion(url_base, max_result, offset)
        print(f"Procesant URL: {url_paginada}")
        ofertes = scrap_ofertas_filtradas(url_paginada, filtro_frases=filtro_frases, dias_maximo=dias_maximo)
        if not ofertes:
            break
        totes_ofertes.extend(ofertes)
        if len(ofertes) < max_result:
            break
        offset += max_result
    return totes_ofertes

# ============================================================
# Funció per detectar ofertes noves i actualitzacions
# ============================================================
def detectar_ofertes(current_offers, archivo_json):
    """
    Es consideraran només les ofertes que compleixin:
      - (concepte == "Tipus de documents" i categoria == "Convocatòria" i subcategoria == "Selecció de PAS")
      o que tinguin "seguiment" True.
    La comparació es realitza utilitzant idEdicte.
    
    Retorna una tupla amb (ofertes_noves, ofertes_actualitzades).
    """
    # Filtrar ofertes que compleixen la condició
    ofertes_filtrades = [offer for offer in current_offers 
                         if (offer.get("concepte") == "Tipus de documents" and 
                             offer.get("categoria") == "Convocatòria" and 
                             offer.get("subcategoria") == "Selecció de PAS")
                         or offer.get("seguiment", False)]
    
    if os.path.exists(archivo_json):
        with open(archivo_json, 'r', encoding='utf-8') as f:
            ofertes_previes = json.load(f)
        # Incloure només els registres amb la clau "idEdicte"
        prev_dict = {offer["idEdicte"]: offer for offer in ofertes_previes if "idEdicte" in offer}
    else:
        prev_dict = {}
    
    ofertes_noves = []
    ofertes_actualitzades = []
    
    for offer in ofertes_filtrades:
        idEdicte = offer.get("idEdicte")
        if idEdicte not in prev_dict:
            ofertes_noves.append(offer)
        else:
            # Si ja existeix i està en seguiment, es considera actualització
            if offer.get("seguiment", False):
                ofertes_actualitzades.append(offer)
    
    # Actualitzar el fitxer JSON amb les ofertes filtrades
    with open(archivo_json, 'w', encoding='utf-8') as f:
        json.dump(ofertes_filtrades, f, ensure_ascii=False, indent=4)
    
    return ofertes_noves, ofertes_actualitzades

# ============================================================
# Funció per enviar missatges via Telegram
# ============================================================
def send_telegram_message(message, token=TELEGRAM_BOT_TOKEN, chat_id=TELEGRAM_CHAT_ID):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message}
    response = requests.post(url, json=payload, headers=HEADERS)
    response.raise_for_status()

# ============================================================
# Funció per generar el missatge a enviar per cada oferta
# ============================================================
def generar_missatge(offer):
    missatge = (
        f"• Títol: {offer.get('titulo')}\n"
        f"• Data Publicació: {offer.get('fecha_publicacion')}\n"
        f"• Estat: {offer.get('estado')}\n"
        f"• Enllaç: {offer.get('enlace')}\n"
        f"• Concepte: {offer.get('concepte')}\n"
        f"• Categoria: {offer.get('categoria')}\n"
        f"• Subcategoria: {offer.get('subcategoria')}\n"
        f"• idEdicte: {offer.get('idEdicte')}\n"
        f"• Seguiment: {offer.get('seguiment')}\n"
        f"• Universitat: {offer.get('universitat', '')}\n"
    )
    return missatge

# ============================================================
# Funció per processar comandes de Telegram
# ============================================================
def process_telegram_commands():
    """
    Consulta les comandes pendents a Telegram.
    Si es rep la comanda "/seguiment {idEdicte}", s'actualitza el fitxer JSON per
    marcar aquesta oferta amb "seguiment": True i s'envia un missatge de confirmació.
    """
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
    except Exception as e:
        print(f"Error en obtenir comandes de Telegram: {e}")
        return
    
    updates = response.json().get("result", [])
    last_update_id = None

    if os.path.exists(JSON_FILE):
        with open(JSON_FILE, 'r', encoding='utf-8') as f:
            ofertes_guardades = json.load(f)
    else:
        ofertes_guardades = []

    for update in updates:
        message = update.get("message", {})
        text = message.get("text", "")
        if text.startswith("/seguiment"):
            parts = text.split()
            if len(parts) >= 2:
                idEdicte_cmd = parts[1].strip()
                trobat = False
                for oferta in ofertes_guardades:
                    if oferta.get("idEdicte") == idEdicte_cmd:
                        oferta["seguiment"] = True
                        trobat = True
                        send_telegram_message(f"Seguiment activat per idEdicte {idEdicte_cmd}")
                        print(f"Seguiment activat per idEdicte {idEdicte_cmd}")
                        break
                if not trobat:
                    send_telegram_message(f"No s'ha trobat oferta amb idEdicte {idEdicte_cmd}")
                    print(f"No s'ha trobat oferta amb idEdicte {idEdicte_cmd}")
        update_id = update.get("update_id")
        if last_update_id is None or update_id > last_update_id:
            last_update_id = update_id

    if last_update_id is not None:
        url_offset = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates?offset={last_update_id+1}"
        try:
            requests.get(url_offset, headers=HEADERS)
        except Exception as e:
            print(f"Error en actualitzar offset: {e}")

    with open(JSON_FILE, 'w', encoding='utf-8') as f:
        json.dump(ofertes_guardades, f, ensure_ascii=False, indent=4)

# ============================================================
# Funció principal (executa la verificació una sola vegada)
# ============================================================
def main():
    # Processar primer les comandes pendents de Telegram per actualitzar el seguiment
    process_telegram_commands()

    # Obtenir ofertes de les dues fonts
    edictes = get_edictes()  # Font UAB
    ofertes_scrap = scrap_totes_ofertes(SCRAP_URL_BASE)  # Font UB
    current_offers = edictes + ofertes_scrap

    # Detectar ofertes noves i actualitzacions aplicant la condició:
    # Inclou només ofertes que compleixin: "Tipus de documents", "Convocatòria" i "Selecció de PAS",
    # o que ja estiguin en seguiment (seguiment True).
    noves, actualitzades = detectar_ofertes(current_offers, JSON_FILE)
    
    # Enviar missatges separats per Ofertes Noves i Actualitzacions.
    if noves:
        header_new = "===== Ofertes Noves =====\n"
        missatge_new = header_new + "\n".join(generar_missatge(offer) for offer in noves)
        send_telegram_message(missatge_new)
        print("Notificacions enviades per Ofertes Noves:")
        for offer in noves:
            print(f"- {offer.get('titulo')}")
    else:
        print("No s'han detectat Ofertes Noves.")
    
    if actualitzades:
        header_update = "===== Actualitzacions =====\n"
        missatge_update = header_update + "\n".join(generar_missatge(offer) for offer in actualitzades)
        send_telegram_message(missatge_update)
        print("Notificacions enviades per Actualitzacions:")
        for offer in actualitzades:
            print(f"- {offer.get('titulo')}")
    else:
        print("No s'han detectat Actualitzacions.")

if __name__ == "__main__":
    main()
