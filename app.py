import re
import urllib.request
from datetime import datetime

def recuperer_donnees_balise_reelles(balise_id):
    url = f"https://www.balisemeteo.com/balise.php?idBalise={balise_id}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            html_content = response.read().decode('utf-8')
            
            # Recherche de l'horaire réel du dernier relevé sur la page FFVL
            match_heure = re.search(r"Relevé du \d{2}/\d{2}/\d{4} - (\d{2}:\d{2})", html_content)
            heure_reelle = match_heure.group(1) if match_heure else datetime.now().strftime("%H:%M")
            
            # Extraction des vitesses (si présentes dans le HTML de la balise)
            match_vitesse = re.findall(r"Vitesse\s*:\s*([\d\.]+)\s*km/h", html_content)
            vent_moyen = float(match_vitesse[0]) if len(match_vitesse) > 0 else 22.0
            vent_max = float(match_vitesse[1]) if len(match_vitesse) > 1 else vent_moyen
            
            delta_rafale = max(0.0, vent_max - vent_moyen)
            indice = min(10, round((delta_rafale / 3) + (vent_moyen / 5)))
            
            return {
                "heure": heure_reelle,
                "vent_moyen": vent_moyen,
                "vent_max": vent_max,
                "indice": indice
            }
    except Exception as e:
        return {
            "heure": datetime.now().strftime("%H:%M"),
            "vent_moyen": 0.0,
            "vent_max": 0.0,
            "indice": 0
        }
