#!/usr/bin/env python3
import requests
import json
import uuid
import os
import hashlib
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse

# ============================================================
# Parámetros globales para ambas fuentes
# ============================================================

# Fuente UAB: API de edictes
API_URL = "https://tauler.seu-e.cat/api/edictes?page=0&size=25&sort=dataPublicacioEfectiva%2Cdesc&ens=11&locale=ca"
BASE_ENLACE_EDICTES = "https://tauler.seu-e.cat/detall?idEns=11&idEdicte="
FILTER_CLASSIFICATION = "Selecció de PAS"
# Ahora se usa una lista de palabras clave para filtrar el título de la convocatoria
FILTER_TITLE_KEYWORDS = ["sociologia", "polítiques"]
MAX_DAYS_API = 3  # Se consideran ofertas publicadas hace menos de 3 días

# Fuente UB: Scraping de ofertas
SCRAP_URL_BASE = "https://seu.ub.edu/ofertaPublicaCategoriaPublic/categories?tipus=totes&text=sociologia&estat=Oberta&tipusOferta=59158&dataOfertaPublicaFilter=dataPublicacio&ordreOfertaPublicaFilter=desc.label"
# Lista de palabras clave para filtrar el título en el scraping
SCRAP_FILTER_PHRASES = ["sociologia", "polítiques"]
MAX_DAYS_SCRAP = 30  # Ofertas de hasta 30 días
MAX_RESULT_SCRAP = 100  # Resultados máximos por página
JSON_FILE = "ofertas_sociologia.json"  # Archivo para almacenar el histórico y detectar novedades

# Parámetros para Telegram
TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN"  # Reemplaza por tu token
TELEGRAM_CHAT_ID = "YOUR_CHAT_ID"      # Reemplaza por el chat id

# ============================================================
# Función para generar idEdicte numérico a partir de los 10 primeros caracteres del título (para UB)
# ============================================================
def generar_id_numeric(titulo):
    """
    Genera un id numérico de 10 dígitos a partir de los 10 primeros caracteres del título.
    Se utiliza SHA‑256 y se extraen los 10 primeros dígitos de su valor numérico.
    """
    partial = titulo[:10]
    hash_val = hashlib.sha256(partial.encode()).hexdigest()
    numeric_id = str(int(hash_val, 16))[:10]
    return numeric_id

# ============================================================
# Funciones para obtener edictes desde el API (UAB)
# ============================================================
def get_edictes():
    response = requests.get(API_URL)
    response.raise_for_status()
    data = response.json()
    edictes = data.get("edictes", [])
    resultados = []
    now = datetime.now()
    
    for edicte in edictes:
        id_api = edicte.get("id_edicte", "")
        titulo = edicte.get("titol", "")
        
        # Filtrar por clasificación
        classificacions = edicte.get("classificacions", [])
        matching_class = next((cl for cl in classificacions if cl.get("subcategoria") == FILTER_CLASSIFICATION), None)
        if not matching_class:
            continue

        # Comprobar si el título contiene al menos una palabra clave de FILTER_TITLE_KEYWORDS
        if not any(keyword.lower() in titulo.lower() for keyword in FILTER_TITLE_KEYWORDS):
            continue

        # Filtrar por fecha de publicación (oferta publicada hace menos de MAX_DAYS_API días)
        fecha_publicacion = edicte.get("data_publicacio", "")
        try:
            fecha_dt = datetime.strptime(fecha_publicacion, "%Y-%m-%d")
        except ValueError:
            continue
        if (now - fecha_dt).days >= MAX_DAYS_API:
            continue
        
        # Extraer estado, enlace y campos de clasificación
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
            "idEdicte": id_api,  # Se guarda el idEdicte real de la API
            "seguiment": False,
            "universitat": "UAB"
        })
    return resultados

# ============================================================
# Funciones para hacer scraping en la fuente de ofertas (UB)
# ============================================================
def scrap_ofertas_filtradas(url, filtro_frases=SCRAP_FILTER_PHRASES, dias_maximo=MAX_DAYS_SCRAP):
    response = requests.get(url)
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
        
        titulo_tag = celdas[0].find('a')
        if titulo_tag:
            titulo = titulo_tag.get_text(strip=True)
            enlace = urljoin(url, titulo_tag.get('href', '').strip())
        else:
            titulo = celdas[0].get_text(strip=True)
            enlace = ""
        
        fecha_publicacion_str = celdas[1].get_text(strip=True)
        estado = celdas[3].get_text(strip=True)
        
        # Solo se consideran ofertas en estado "oberta"
        if estado.lower() != "oberta":
            continue
        
        # Comprobar si el título contiene al menos una de las frases de filtro
        if not any(keyword.lower() in titulo.lower() for keyword in filtro_frases):
            continue
        
        try:
            fecha_publicacion = datetime.strptime(fecha_publicacion_str, "%d-%m-%Y").date()
        except ValueError:
            continue
        
        if fecha_limite <= fecha_publicacion <= hoy:
            # Para UB, se genera idEdicte a partir del título
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

def scrap_todas_ofertas(url_base, filtro_frases=SCRAP_FILTER_PHRASES, dias_maximo=MAX_DAYS_SCRAP, max_result=MAX_RESULT_SCRAP):
    todas_ofertas = []
    offset = 0
    while True:
        url_paginada = construir_url_con_paginacion(url_base, max_result, offset)
        print(f"Procesando URL: {url_paginada}")
        ofertas = scrap_ofertas_filtradas(url_paginada, filtro_frases=filtro_frases, dias_maximo=dias_maximo)
        if not ofertas:
            break
        todas_ofertas.extend(ofertas)
        if len(ofertas) < max_result:
            break
        offset += max_result
    return todas_ofertas

# ============================================================
# Función para detectar ofertas nuevas y actualizaciones
# ============================================================
def detectar_ofertas(current_offers, archivo_json):
    """
    Se incluirán solo las ofertas que cumplan:
      - (concepte == "Tipus de documents" and categoria == "Convocatòria" and subcategoria == "Selecció de PAS")
      o bien, que tengan "seguiment" True.
    Se retorna una tupla con:
      (ofertas_nuevas, ofertas_actualizadas)
    
    La comparación se realiza usando el idEdicte.
    """
    # Filtrar ofertas que cumplen la condición
    ofertas_filtradas = [offer for offer in current_offers 
                           if (offer.get("concepte") == "Tipus de documents" and 
                               offer.get("categoria") == "Convocatòria" and 
                               offer.get("subcategoria") == "Selecció de PAS")
                           or offer.get("seguiment", False)]
    
    # Cargar ofertas previas desde el JSON (si existen)
    if os.path.exists(archivo_json):
        with open(archivo_json, 'r', encoding='utf-8') as f:
            ofertas_previas = json.load(f)
        # Sólo se incluyen aquellos registros que tengan la clave "idEdicte"
        prev_dict = {offer["idEdicte"]: offer for offer in ofertas_previas if "idEdicte" in offer}
    else:
        prev_dict = {}
    
    ofertas_nuevas = []
    ofertas_actualizadas = []
    
    for offer in ofertas_filtradas:
        idEdicte = offer.get("idEdicte")
        if idEdicte not in prev_dict:
            ofertas_nuevas.append(offer)
        else:
            # Si ya existe y está en seguiment, se considera actualización.
            if offer.get("seguiment", False):
                ofertas_actualizadas.append(offer)
    
    # Actualizar el archivo JSON con las ofertas filtradas (cumpliendo la condición)
    with open(archivo_json, 'w', encoding='utf-8') as f:
        json.dump(ofertas_filtradas, f, ensure_ascii=False, indent=4)
    
    return ofertas_nuevas, ofertas_actualizadas

# ============================================================
# Función para enviar mensajes vía Telegram
# ============================================================
def send_telegram_message(message, token=TELEGRAM_BOT_TOKEN, chat_id=TELEGRAM_CHAT_ID):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message}
    response = requests.post(url, json=payload)
    response.raise_for_status()

# ============================================================
# Función para generar el mensaje a enviar para cada oferta
# ============================================================
def generar_mensaje(oferta):
    mensaje = (
        f"• Título: {oferta.get('titulo')}\n"
        f"• Fecha Publicación: {oferta.get('fecha_publicacion')}\n"
        f"• Estado: {oferta.get('estado')}\n"
        f"• Enlace: {oferta.get('enlace')}\n"
        f"• Concepte: {oferta.get('concepte')}\n"
        f"• Categoría: {oferta.get('categoria')}\n"
        f"• Subcategoría: {oferta.get('subcategoria')}\n"
        f"• idEdicte: {oferta.get('idEdicte')}\n"
        f"• Seguiment: {oferta.get('seguiment')}\n"
        f"• Universitat: {oferta.get('universitat', '')}\n"
    )
    return mensaje

# ============================================================
# Función para procesar comandos de Telegram
# ============================================================
def process_telegram_commands():
    """
    Consulta los comandos pendientes en Telegram.
    Si se recibe el comando "/seguiment {idEdicte}", se actualiza el JSON para
    marcar esa oferta con "seguiment": True y se envía un mensaje de confirmación.
    """
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    try:
        response = requests.get(url)
        response.raise_for_status()
    except Exception as e:
        print(f"Error al obtener comandos de Telegram: {e}")
        return
    
    updates = response.json().get("result", [])
    last_update_id = None

    # Cargar ofertas almacenadas desde JSON
    if os.path.exists(JSON_FILE):
        with open(JSON_FILE, 'r', encoding='utf-8') as f:
            ofertas_guardadas = json.load(f)
    else:
        ofertas_guardadas = []

    for update in updates:
        message = update.get("message", {})
        text = message.get("text", "")
        if text.startswith("/seguiment"):
            parts = text.split()
            if len(parts) >= 2:
                idEdicte_cmd = parts[1].strip()
                encontrado = False
                for oferta in ofertas_guardadas:
                    if oferta.get("idEdicte") == idEdicte_cmd:
                        oferta["seguiment"] = True
                        encontrado = True
                        send_telegram_message(f"Seguiment activado para idEdicte {idEdicte_cmd}")
                        print(f"Seguiment activado para idEdicte {idEdicte_cmd}")
                        break
                if not encontrado:
                    send_telegram_message(f"No se encontró oferta con idEdicte {idEdicte_cmd}")
                    print(f"No se encontró oferta con idEdicte {idEdicte_cmd}")
        update_id = update.get("update_id")
        if last_update_id is None or update_id > last_update_id:
            last_update_id = update_id

    # Marcar los updates leídos para no procesarlos de nuevo
    if last_update_id is not None:
        url_offset = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates?offset={last_update_id+1}"
        try:
            requests.get(url_offset)
        except Exception as e:
            print(f"Error al actualizar offset: {e}")

    # Guardar modificaciones en el JSON (si hubo cambios en seguiment)
    with open(JSON_FILE, 'w', encoding='utf-8') as f:
        json.dump(ofertas_guardadas, f, ensure_ascii=False, indent=4)

# ============================================================
# Función principal (ejecuta la verificación una sola vez)
# ============================================================
def main():
    # Primero, procesar comandos pendientes de Telegram (para actualizar seguiment)
    process_telegram_commands()

    # Obtener ofertas de ambas fuentes
    edictes = get_edictes()  # Fuente UAB
    ofertas_scrap = scrap_todas_ofertas(SCRAP_URL_BASE)  # Fuente UB
    current_offers = edictes + ofertas_scrap

    # Detectar ofertas nuevas y actualizaciones aplicando la condición:
    # Solo se incluyen si (concepte, categoria, subcategoria) son:
    # "Tipus de documents", "Convocatòria", "Selecció de PAS",
    # o si el seguimiento ya está activado (seguiment True).
    nuevas, actualizadas = detectar_ofertas(current_offers, JSON_FILE)
    
    # Enviar mensajes separados para Ofertas Nuevas y Actualizaciones.
    if nuevas:
        header_new = "===== Ofertas Nuevas =====\n"
        mensaje_new = header_new + "\n".join(generar_mensaje(offer) for offer in nuevas)
        send_telegram_message(mensaje_new)
        print("Notificaciones enviadas para Ofertas Nuevas:")
        for offer in nuevas:
            print(f"- {offer.get('titulo')}")
    else:
        print("No se han detectado Ofertas Nuevas.")
    
    if actualizadas:
        header_update = "===== Actualizaciones =====\n"
        mensaje_update = header_update + "\n".join(generar_mensaje(offer) for offer in actualizadas)
        send_telegram_message(mensaje_update)
        print("Notificaciones enviadas para Actualizaciones:")
        for offer in actualizadas:
            print(f"- {offer.get('titulo')}")
    else:
        print("No se han detectado Actualizaciones.")

if __name__ == "__main__":
    main()
