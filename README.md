# Bot OfertesUni per a Convocatòries Universitàries

Aquest projecte conté un script en **Python** que consulta i filtra convocatòries de dues fonts (l’API d’edictes de la **UAB** i l’scraping de la **UB**) per detectar processos de **Selecció de PAS**. El sistema envia notificacions mitjançant un bot de **Telegram** i permet marcar convocatòries per rebre actualitzacions amb el comandament `/seguiment {idSeguiment}`.

---

## Característiques principals

* **Consulta d’ofertes**

  * Obté ofertes des de l’API de la UAB i mitjançant scraping de la web de la UB.
  * Aplica filtres per incloure només les ofertes que siguin:

    * Convocatòries amb `concepte = "Tipus de documents"`, `categoria = "Convocatòria"` i `subcategoria = "Selecció de PAS"`.
    * **O** que estiguin marcades per seguiment (`"seguiment": true`).

* **Filtrat per paraules clau**
  Permet definir llistes de paraules clau per filtrar el títol de l’oferta (p. ex. `["sociologia", "polítiques"]`).

* **Notificacions via Telegram**
  Envia dos tipus de missatges diferenciats:

  1. **Ofertes noves** – convocatòries detectades per primera vegada.
  2. **Actualitzacions** – ofertes ja existents i marcades amb seguiment que han canviat.

* **Gestió de seguiment**

  * Amb `/seguiment {idSeguiment}` es marca per seguiment la convocatòria identificada per **idSeguiment** (la primera paraula del títol, sense modificar).
  * Qualsevol nova oferta amb el mateix `idSeguiment` generarà avisos d’“Actualització”.

* **Persistència JSON**
  Les ofertes processades es desen a `ofertas_sociologia.json`, utilitzant **l’enllaç** com a clau única i el camp `idSeguiment` per al seguiment.

---

## Requisits

* **Python 3.7** o superior
* **Dependències Python**

  * `requests`
  * `beautifulsoup4`
* **Accés a Internet** per consultar l’API i fer scraping.
* **Compte i bot de Telegram** amb:

  * `TELEGRAM_BOT_TOKEN`
  * `TELEGRAM_CHAT_ID`

---

## Instal·lació

1. **Descarrega el script**
   Clona aquest repositori o baixa `OfertesUniBot.py` al teu sistema.
2. **Instal·la les dependències**

   ```bash
   pip install requests beautifulsoup4
   ```
3. **Configura el script**

   * Edita `OfertesUniBot.py` i substitueix:

     * `TELEGRAM_BOT_TOKEN` pel token del teu bot.
     * `TELEGRAM_CHAT_ID` pel xat on vols rebre notificacions.
   * Ajusta opcionalment les llistes de paraules clau (`FILTER_TITLE_KEYWORDS`, `SCRAP_FILTER_PHRASES`) i altres paràmetres globals (`MAX_DAYS_API`, `MAX_DAYS_SCRAP`).

---

## Ús

El script s’executa (p. ex. un cop al dia) i realitza:

1. **Processament de comandes Telegram**

   * Llegeix comandes pendents.
   * Si rep `/seguiment {idSeguiment}`, marca totes les ofertes amb el mateix `idSeguiment` com a `"seguiment": true` i confirma.

2. **Obtenció d’ofertes**

   * Consulta UAB (API) i UB (scraping).
   * Assigna `idSeguiment = primera paraula del títol`.

3. **Filtrat d’ofertes**

   * Inclou només les que compleixin els criteris de convocatòria **o** tinguin seguiment actiu.

4. **Detecció de novetats i actualitzacions**

   * Compara l’històric (JSON) amb les noves dades.
   * Classifica en “Ofertes noves” i “Actualitzacions” (mateix `idSeguiment` amb seguiment actiu).

5. **Enviament de notificacions Telegram** quan correspongui.

### Execució manual

```bash
python3 /ruta/al/script/OfertesUniBot.py
```

### Programació amb cron (exemple a Raspbian)

```bash
crontab -e
# Executar cada dia a les 08:00 i guardar log
0 8 * * * python3 /ruta/al/script/OfertesUniBot.py >> /ruta/al/log_script.log 2>&1
```

---

## Comandes de Telegram

| Comanda                    | Descripció                                                                |
| -------------------------- | ------------------------------------------------------------------------- |
| `/seguiment {idSeguiment}` | Activa el seguiment per a totes les ofertes amb el `idSeguiment` indicat. |

> Exemple:
>
> ```
> /seguiment 2025PILIFRUA80
> ```

---

## Estructura de `ofertas_sociologia.json`

```json
{
  "titulo": "Títol de la convocatòria",
  "fecha_publicacion": "AAAA-MM-DD",
  "estado": "Oberta | Tancada | ...",
  "enlace": "URL de la convocatòria",
  "concepte": "Tipus de documents",
  "categoria": "Convocatòria",
  "subcategoria": "Selecció de PAS",
  "idSeguiment": "2025PILIFRUA80",
  "seguiment": false,
  "universitat": "UAB" // o "UB"
}
```

---

## Notes addicionals

* Si canvia l’estructura de la web o l’API, pot caldre ajustar el codi de filtratge o scraping.
* Si el JSON es corromp, es pot eliminar per regenerar-lo en la següent execució.
* Redirecciona la sortida del script a un fitxer de log per facilitar la depuració.

---

## Llicència

Projecte distribuït amb finalitats educatives. Lliure de modificar segons necessitats.

---

## Contacte

Qualsevol dubte o suggeriment: \[[oriollarrea111@gmail.com](mailto:oriollarrea111@gmail.com)] o obre un issue al repositori.
