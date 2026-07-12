import streamlit as st
import urllib.request
import json
from datetime import datetime, timedelta

# --- CONFIGURATION DE LA PAGE STREAMLIT ---
st.set_page_config(page_title="WeatherFly - Assistant Vol Libre", layout="wide")

# --- BASE DE DONNÉES AVEC ASSOCIATION BALISE FFVL (ID ou URL) ---
SPOTS_HIERARCHIE = {
    "Occitanie": {
        "09 - Ariège": {
            "Port de Lers": {
                "lat": 42.8036, "lon": 1.3711, "deco": ["NO"], "interdit_sud": True,
                "balise_ffvl_id": None, # Remplacer par l'ID de la balise si connu (ex: "portdelers")
                "conseil_site": "⚠️ Le Port de Lers peut forcir très vite en thermique. Reste vigilant aux cycles. Sensible au vent de Sud > 10 km/h (DANGER)."
            },
            "Moulis / Char de Moulis": {
                "lat": 42.9564, "lon": 1.0903, "deco": ["N"], "interdit_sud": False,
                "balise_ffvl_id": None,
                "conseil_site": "Brise de vallée classique. Attention au vent météo d'Ouest qui peut culer au déco."
            }
        }
    },
    "Bretagne": {
        "29 - Finistère": {
            "Ménez Hom": {
                "lat": 48.2167, "lon": -4.1000, "deco": ["O", "N"], "interdit_sud": False,
                "balise_ffvl_id": None, # Mettre l'identifiant FFVL si disponible
                "conseil_site": "Colline emblématique bretonne, vol dynamique par vent d'ouest ou nord."
            }
        }
    }
}

COMPASS_ANGLES = {"N": 0, "NE": 45, "E": 90, "SE": 135, "S": 180, "SO": 225, "O": 270, "NO": 315}

def convertir_degres_en_direction(degres):
    if (degres >= 337.5) or (degres < 22.5): return "N"
    if 22.5 <= degres < 67.5: return "NE"
    if 67.5 <= degres < 112.5: return "E"
    if 112.5 <= degres < 157.5: return "SE"
    if 157.5 <= degres < 202.5: return "S"
    if 202.5 <= degres < 247.5: return "SO"
    if 247.5 <= degres < 292.5: return "O"
    return "NO"

def valider_axe_vent(direction_vent, orientations_deco):
    if isinstance(orientations_deco, str):
        orientations_deco = [orientations_deco]
        
    angle_vent = COMPASS_ANGLES[direction_vent]
    for d_deco in orientations_deco:
        angle_deco = COMPASS_ANGLES[d_deco]
        ecart = abs(angle_vent - angle_deco)
        if ecart > 180: ecart = 360 - ecart
        if ecart <= 45:
            return True
    return False

def recuperer_releves_ffvl(balise_id):
    """Interroge les flux JSON officiels de la FFVL pour le temps réel."""
    if not balise_id:
        return None
    url_releves = "https://data.ffvl.fr/json/relevesmeteo.json"
    try:
        req = urllib.request.Request(url_releves, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            # Recherche de la balise spécifique dans le flux de relevés
            if balise_id in data:
                return data[balise_id]
    except Exception:
        pass
    return None

def recuperer_vraie_meteo(lat, lon, date_str):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&start_date={date_str}&end_date={date_str}&hourly=temperature_2m,wind_speed_10m,wind_gusts_10m,wind_direction_10m,precipitation,cape&wind_speed_unit=kmh&timezone=Europe%2FParis"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=20) as response:
            data = json.loads(response.read().decode())
            return data.get("hourly", {})
    except Exception as e:
        st.error(f"Erreur d'accès direct à l'API météo : {e}")
        return {}

# --- INTERFACE UTILISATEUR (STREAMLIT) ---
st.title("WeatherFly - Assistant Vol Libre (+ Balises FFVL)")

# Construction simplifiée des listes pour l'exemple global
regions = list(SPOTS_HIERARCHIE.keys())
region_selectionnee = st.selectbox("Région :", regions)
departements = list(SPOTS_HIERARCHIE[region_selectionnee].keys())
dept_selectionne = st.selectbox("Département :", departements)
sites = list(SPOTS_HIERARCHIE[region_selectionnee][dept_selectionne].keys())
spot_name = st.selectbox("Site officiel :", sites)

spot_config = SPOTS_HIERARCHIE[region_selectionnee][dept_selectionne][spot_name]
date_selectionnee = st.selectbox("Date du vol :", [(datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(5)])
ploufs = st.number_input("Expérience (Nb de ploufs) :", min_value=0, max_value=1000, value=25)

m_oreilles = st.checkbox("Oreilles maîtrisées")
m_face = st.checkbox("Face voile (>15km/h)")

analyser_clic = st.button("RECHERCHER ET ANALYSER", type="primary")

if analyser_clic:
    est_aujourdhui = (date_selectionnee == datetime.now().strftime("%Y-%m-%d"))
    releve_actuel = None
    
    if est_aujourdhui and spot_config.get("balise_ffvl_id"):
        with st.spinner("Lecture de la balise FFVL en temps réel..."):
            releve_actuel = recuperer_releves_ffvl(spot_config["balise_ffvl_id"])

    with st.spinner("Récupération des modèles météo horaires..."):
        hourly_data = recuperer_vraie_meteo(spot_config["lat"], spot_config["lon"], date_selectionnee)
    
    if hourly_data and "time" in hourly_data:
        st.success("Analyse aérologique générée avec succès.")
        if releve_actuel:
            st.info(f"📡 **Donnée balise FFVL en direct :** Vent moyen mesuré à {releve_actuel.get('vent_moy')} km/h.")
        else:
            st.write("Utilisation des prévisions standard de la journée.")
