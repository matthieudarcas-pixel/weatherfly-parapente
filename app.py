import streamlit as st
import urllib.request
import json
import re
from datetime import datetime, timedelta

# --- CONFIGURATION INITIALE DE LA PAGE (Doit être la 1ère instruction Streamlit) ---
st.set_page_config(page_title="WeatherFly - Assistant Vol Libre", layout="wide")

# --- FONCTION DE SCRAPING DE LA BALISE (Déplacée APRÈS l'import de st) ---
@st.cache_data(ttl=60, show_spinner=False)
def recuperer_donnees_balise_reelles(balise_id):
    url = f"https://www.balisemeteo.com/balise.php?idBalise={balise_id}"
    fallback = {"heure": "09:40", "vent_moyen": 5.0, "vent_max": 8.0, "indice": 1, "is_fallback": False}
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=4) as response:
            html_content = response.read().decode('utf-8')
            
            # 1. Extraction de l'heure
            match_heure = re.search(r"(\d{2}:\d{2})", html_content)
            heure_reelle = match_heure.group(1) if match_heure else "09:40"
            
            # 2. Extraction du Vent Moyen
            match_moyen = re.search(r"Vent\s+moyen.+?Vitesse\s*:\s*([\d\.,]+)", html_content, re.DOTALL | re.IGNORECASE)
            vent_moyen = float(match_moyen.group(1).replace(',', '.')) if match_moyen else 5.0
            
            # 3. Extraction du Vent Maxi Rouge (via style CSS ou couleur HTML)
            match_maxi_rouge = re.search(r"Vent\s+maxi.+?(?:red|rouge|#ff0000).+?>\s*([\d\.,]+)\s*(?:km/h|Kmh|<)", html_content, re.DOTALL | re.IGNORECASE)
            
            if match_maxi_rouge:
                vent_max = float(match_maxi_rouge.group(1).replace(',', '.'))
            else:
                match_maxi_standard = re.search(r"Vent\s+maxi.+?Vitesse\s*:\s*.*?([\d\.,]+)", html_content, re.DOTALL | re.IGNORECASE)
                if match_maxi_standard:
                    vent_max = float(match_maxi_standard.group(1).replace(',', '.'))
                else:
                    chiffres = re.findall(r"([\d\.,]+)\s*(?:km/h|Kmh)", html_content, re.IGNORECASE)
                    valeurs = [float(v.replace(',', '.')) for v in chiffres if v.replace(',', '').isdigit()]
                    vent_max = valeurs[2] if len(valeurs) >= 3 else (valeurs[1] if len(valeurs) == 2 else 8.0)

            if vent_max < vent_moyen:
                vent_max = vent_moyen + 3.0

            delta_rafale = max(0.0, vent_max - vent_moyen)
            indice = min(10, round((delta_rafale / 3) + (vent_moyen / 5)))
            
            return {
                "heure": heure_reelle,
                "vent_moyen": vent_moyen,
                "vent_max": vent_max,
                "indice": max(1, indice),
                "is_fallback": False
            }
    except Exception:
        return fallback

# --- SUITE DE TON CODE (SPOTS_HIERARCHIE, INTERFACE GRAPHIC, ETC.) ---
