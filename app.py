import streamlit as st
import urllib.request
import json
from datetime import datetime, timedelta

st.set_page_config(page_title="WeatherFly - Assistant Vol Libre", layout="wide")

# --- CHARGEMENT DYNAMIQUE DES SITES DEPUIS L'OPEN DATA FFVL ---
@st.cache_data(ttl=86400)
def charger_catalogue_ffvl():
    # URL du fichier officiel des sites de pratique de la FFVL sur data.gouv.fr / data.ffvl.fr
    url_data = "https://data.ffvl.fr/export/sites.json" # ou dataset équivalent
    try:
        req = urllib.request.Request(url_data, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as response:
            brut = json.loads(response.read().decode())
            # Transformation au format hiérarchique Région -> Département -> Site
            hierarchie = {}
            for site in brut:
                region = site.get("region", "Autres")
                dept = f"{site.get('code_dept', '00')} - {site.get('departement', 'Inconnu')}"
                nom = site.get("nom", "Site sans nom")
                
                if region not in hierarchie: hierarchie[region] = {}
                if dept not in hierarchie[region]: hierarchie[region][dept] = {}
                
                hierarchie[region][dept][nom] = {
                    "lat": float(site.get("latitude", 45.0)),
                    "lon": float(site.get("longitude", 6.0)),
                    "deco": site.get("orientation", "O").split("/")[0].strip().upper(),
                    "interdit_sud": site.get("orientation", "").upper().find("S") != -1 and site.get("danger_sud", False),
                    "conseil_site": site.get("remarques", "Consulter les fiches officielles de la FFVL pour les particularités aéro.")
                }
            return hierarchie
    except Exception:
        # Repli de sécurité si l'API data de la FFVL est temporairement injoignable
        return {
            "Occitanie": {
                "09 - Ariège": {
                    "Port de Lers": {"lat": 42.8036, "lon": 1.3711, "deco": "NO", "interdit_sud": True, "conseil_site": "Attention au thermique fort."}
                }
            }
        }

SPOTS_HIERARCHIE = charger_catalogue_ffvl()
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

def valider_axe_vent(direction_vent, direction_deco):
    if direction_deco not in COMPASS_ANGLES or direction_vent not in COMPASS_ANGLES: return True
    angle_vent = COMPASS_ANGLES[direction_vent]
    angle_deco = COMPASS_ANGLES[direction_deco]
    ecart = abs(angle_vent - angle_deco)
    if ecart > 180: ecart = 360 - ecart
    return ecart <= 45

def recuperer_vraie_meteo(lat, lon, date_str):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&start_date={date_str}&end_date={date_str}&hourly=temperature_2m,wind_speed_10m,wind_gusts_10m,wind_direction_10m,precipitation,cape&wind_speed_unit=kmh&timezone=Europe%2FParis"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=20) as response:
            return json.loads(response.read().decode()).get("hourly", {})
    except Exception as e:
        st.error(f"Erreur d'accès à l'API météo : {e}")
        return {}

st.title("WeatherFly - Assistant Vol Libre (Flux FFVL Live)")

col_gauche, col_droite = st.columns([3, 2])

with col_gauche:
    st.subheader("Sélection dynamique des sites")
    regions = list(SPOTS_HIERARCHIE.keys())
    region_sel = st.selectbox("Région :", regions, key="reg_live")
    
    departements = list(SPOTS_HIERARCHIE[region_sel].keys())
    dept_sel = st.selectbox("Département :", departements, key="dept_live")
    
    sites = list(SPOTS_HIERARCHIE[region_sel][dept_sel].keys())
    spot_sel = st.selectbox("Site officiel :", sites, key="spot_live")
    
    spot_config = SPOTS_HIERARCHIE[region_sel][dept_sel][spot_sel]
    date_sel = st.selectbox("Date du vol :", [(datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(5)], key="date_live")
    ploufs = st.number_input("Expérience (Nb de ploufs) :", min_value=0, value=15, key="ploufs_live")
    
    if st.button("LANCER L'ANALYSE", type="primary"):
        data = recuperer_vraie_meteo(spot_config["lat"], spot_config["lon"], date_sel)
        if data and "time" in data:
            st.success(f"Analyse prête pour {spot_sel} (Coordonnées : {spot_config['lat']}, {spot_config['lon']})")
        else:
            st.warning("Impossible de récupérer les données météo pour ce site pour le moment.")
