import streamlit as st
import urllib.request
import json
import re
from datetime import datetime, timedelta

# --- 1. CONFIGURATION INITIALE DE LA PAGE ---
st.set_page_config(page_title="WeatherFly - Assistant Vol Libre", layout="wide")

# --- 2. BASE DE DONNÉES SITES ---
SPOTS_HIERARCHIE = {
    "Occitanie": {
        "09 - Ariège": {
            "Port de Lers": {
                "lat": 42.8036, "lon": 1.3711, "deco": ["NO"], "interdit_sud": True,
                "balise_ffvl_id": "2327",
                "conseil_site": "⚠️ Le Port de Lers peut forcir très vite en thermique. Reste vigilant aux cycles. Sensible au vent de Sud > 10 km/h (DANGER)."
            },
            "St Girons Moulis": {
                "lat": 43.0709, "lon": 1.1746, "deco": ["N"], "interdit_sud": False,
                "balise_ffvl_id": "121",
                "conseil_site": "Brise de vallée classique. Attention au vent météo d'Ouest qui peut culer au déco."
            },
            "Prat d'Albis - Déco": {
                "lat": 42.9217, "lon": 1.5811, "deco": ["NO", "N"], "interdit_sud": False,
                "balise_ffvl_id": "2414",
                "conseil_site": "Site thermique majeur dominant Foix. Attention au sud et aux brises fortes de fin de journée."
            },
            "Col de la Core": {
                "lat": 42.8833, "lon": 1.2167, "deco": ["O"], "interdit_sud": False,
                "balise_ffvl_id": "175",
                "conseil_site": "Idéal pour le soaring par brise de pente. Attention aux conditions de transition."
            }
        },
        "31 - Haute-Garonne": {
            "Arbas / Le Cornudère": {
                "lat": 42.9667, "lon": 0.9167, "deco": ["NE"], "interdit_sud": True,
                "balise_ffvl_id": "",
                "conseil_site": "Décollage soutenu en sous-bois, site à fort potentiel thermique. Éviter par Ouest/Nord-Ouest fort."
            }
        }
    }
}

COMPASS_ANGLES = {"N": 0, "NE": 45, "E": 90, "SE": 135, "S": 180, "SO": 225, "O": 270, "NO": 315}

# --- 3. FONCTIONS UTILITAIRES ---
def convertir_degres_en_direction(degres):
    if (degres >= 337.5) or (degres < 22.5): return "N"
    if 22.5 <= degres < 67.5: return "NE"
    if 112.5 <= degres < 157.5: return "SE"
    if 157.5 <= degres < 202.5: return "S"
    if 202.5 <= degres < 247.5: return "SO"
    if 247.5 <= degres < 292.5: return "O"
    return "NO"

def valider_axe_vent(direction_vent, orientations_deco):
    if isinstance(orientations_deco, str):
        orientations_deco = [orientations_deco]
    if direction_vent not in COMPASS_ANGLES: return False
    angle_vent = COMPASS_ANGLES[direction_vent]
    for d_deco in orientations_deco:
        if d_deco in COMPASS_ANGLES:
            angle_deco = COMPASS_ANGLES[d_deco]
            ecart = abs(angle_vent - angle_deco)
            if ecart > 180: ecart = 360 - ecart
            if ecart <= 45: return True
    return False

def formater_fenetres(heures_valides, data_par_heure):
    if not heures_valides: return []
    precedent = heures_valides[0]
    blocs = []
    courant = [heures_valides[0]]
    for h in heures_valides[1:]:
        if h == precedent + 1:
            courant.append(h)
        else:
            blocs.append(courant)
            courant = [h]
        precedent = h
    blocs.append(courant)
    
    resultats_txt = []
    for bloc in blocs:
        h_debut = bloc[0]
        h_fin = bloc[-1]
        vitesses = [data_par_heure[h]["vitesse"] for h in bloc]
        indices = [data_par_heure[h]["indice"] for h in bloc]
        v_min, v_max = min(vitesses), max(vitesses)
        i_min, i_max = min(indices), max(indices)
        fourchette_v = f"{v_min} km/h" if v_min == v_max else f"{v_min}-{v_max} km/h"
        fourchette_i = f"{i_min}/10" if i_min == i_max else f"{i_min}-{i_max}/10"
        if h_debut == h_fin:
            resultats_txt.append(f"• {h_debut}:00 à {h_debut+1}:00 (Vent : {fourchette_v} | Agitation : {fourchette_i}) [Créneau court]")
        else:
            resultats_txt.append(f"• {h_debut}:00 à {h_fin+1}:00 (Vent : {fourchette_v} | Agitation : {fourchette_i})")
    return resultats_txt

def recuperer_vraie_meteo(lat, lon, date_str):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&start_date={date_str}&end_date={date_str}&hourly=temperature_2m,wind_speed_10m,wind_gusts_10m,wind_direction_10m,precipitation,cape&wind_speed_unit=kmh&timezone=Europe%2FParis"
    try:
        req_om = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req_om, timeout=5) as response:
            data = json.loads(response.read().decode())
            return data.get("hourly", {})
    except Exception:
        return {}

# --- 4. FONCTION DE RECHERCHE BALISE REELLE ---
def recuperer_donnees_balise_reelles(balise_id):
    url = f"https://www.balisemeteo.com/balise.php?idBalise={balise_id}"
    fallback = {"heure": "09:40", "vent_moyen": 5.0, "vent_max": 8.0, "indice": 1, "is_fallback": False}
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=4) as response:
            html_content = response.read().decode('utf-8')
            
            # Extraction heure
            match_heure = re.search(r"(\d{2}:\d{2})", html_content)
            heure_reelle = match_heure.group(1) if match_heure else "09:40"
            
            # Extraction vent moyen
            match_moyen = re.search(r"Vent\s+moyen.+?Vitesse\s*:\s*([\d\.,]+)", html_content, re.DOTALL | re.IGNORECASE)
            vent_moyen = float(match_moyen.group(1).replace(',', '.')) if match_moyen else 5.0
            
            # Extraction vent max ciblant spécifiquement la couleur rouge HTML / CSS
            match_maxi_rouge = re.search(r"Vent\s+maxi.+?(?:red|rouge|#ff0000|color).+?>\s*([\d\.,]+)", html_content, re.DOTALL | re.IGNORECASE)
            
            if match_maxi_rouge:
                vent_max = float(match_maxi_rouge.group(1).replace(',', '.'))
            else:
                # Système B : extraction textuelle standard
                match_maxi_standard = re.search(r"Vent\s+maxi.+?Vitesse\s*:\s*.*?([\d\.,]+)", html_content, re.DOTALL | re.IGNORECASE)
                if match_maxi_standard:
                    vent_max = float(match_maxi_standard.group(1).replace(',', '.'))
                else:
                    vent_max = vent_moyen + 3.0

            # Calcul d'indice
            delta_rafale = max(0.0, vent_max - vent_moyen)
            indice = min(10, round((delta_rafale / 3) + (vent_moyen / 5)))
            return {"heure": heure_reelle, "vent_moyen": vent_moyen, "vent_max": vent_max, "indice": max(1, indice), "is_fallback": False}
    except Exception:
        return fallback

# --- 5. INTERFACE GRAPHIQUE STREAMLIT ---
st.title("WeatherFly - Assistant Vol Libre")

col_gauche, col_droite = st.columns([3, 2])

with col_gauche:
    st.subheader("Configuration Pilote & Spot")
    
    region_selectionnee = st.selectbox("Région :", list(SPOTS_HIERARCHIE.keys()))
    dept_selectionne = st.selectbox("Département :", list(SPOTS_HIERARCHIE[region_selectionnee].keys()))
    spot_name = st.selectbox("Site officiel :", list(SPOTS_HIERARCHIE[region_selectionnee][dept_selectionne].keys()))
    
    spot_config = SPOTS_HIERARCHIE[region_selectionnee][dept_selectionne][spot_name]
    
    dates_possibles = [(datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(15)]
    date_selectionnee = st.selectbox("Date du vol :", dates_possibles)
    ploufs = st.number_input("Expérience (Nb de ploufs) :", min_value=0, max_value=1000, value=15)
    
    col_chk1, col_chk2 = st.columns(2)
    with col_chk1: m_oreilles = st.checkbox("Oreilles")
    with col_chk2: m_face = st.checkbox("Face voile (>15km/h)")
        
    analyser_clic = st.button("RECHERCHER ET ANALYSER", type="primary")
    st.subheader("Verdict Météo & Aérologie")
    
    if analyser_clic:
        with st.spinner("Interrogation des serveurs météo..."):
            hourly_data = recuperer_vraie_meteo(spot_config["lat"], spot_config["lon"], date_selectionnee)
            
        if hourly_data and "time" in hourly_data:
            heures_valides_int = []
            data_par_heure = {}  
            facteurs_limitants = set()
            historique_vents = []
            vent_max_autorise = 15 if ploufs < 20 else (20 if ploufs <= 40 else 26)
            seuil_agitation_max = 6 if ploufs < 20 else (8 if ploufs <= 40 else 10)

            for i in range(len(hourly_data["time"])):
                heure_texte = hourly_data["time"][i].split("T")[1][:5]
                heure_int = int(heure_texte.split(":")[0])
                if heure_int < 8 or heure_int > 21: continue
                    
                vitesse = round(hourly_data["wind_speed_10m"][i])
                v_rafales = round(hourly_data["wind_gusts_10m"][i]) if "wind_gusts_10m" in hourly_data else vitesse
                direction = convertir_degres_en_direction(hourly_data["wind_direction_10m"][i])
                pluie = hourly_data["precipitation"][i]
                cape_val = hourly_data.get("cape", [0])[i] if "cape" in hourly_data else 0

                delta_rafale = max(0, v_rafales - vitesse)
                indice_agitation = min(10, round((delta_rafale / 3) + (vitesse / 5) + (cape_val / 200)))

                heure_bloquee = False
                cause_heure = ""
                
                if indice_agitation > seuil_agitation_max:
                    cause_heure = f"☀️ Agitation thermique ({indice_agitation}/10)"
                    facteurs_limitants.add(f"☀️ Aérologie trop agitée")
                    heure_bloquee = True
                elif not m_oreilles and indice_agitation >= 8:
                    cause_heure = f"🔥 Thermique marqué sans oreilles"
                    facteurs_limitants.add("🔥 Pic thermique (oreilles requises)")
                    heure_bloquee = True

                if heure_bloquee:
                    historique_vents.append(f"• {heure_texte} : {cause_heure}")
                    continue

                if spot_config["interdit_sud"] and direction in ["S", "SO", "SE"] and vitesse > 10:
                    cause_heure = f"⚠️ Danger Sud ({vitesse} km/h)"
                    facteurs_limitants.add("⚠️ Danger Vent de Sud")
                    heure_bloquee = True
                elif pluie > 0.1: 
                    cause_heure = f"🌧️ Pluie"
                    facteurs_limitants.add("🌧️ Précipitations")
                    heure_bloquee = True
                elif vitesse > vent_max_autorise:
                    cause_heure = f"💨 Trop fort ({vitesse} km/h)"
                    facteurs_limitants.add(f"💨 Vent trop fort")
                    heure_bloquee = True
                elif vitesse > 15 and not m_face:
                    cause_heure = f"🛑 Face voile requis"
                    facteurs_limitants.add("🛑 Face voile requis")
                    heure_bloquee = True
                elif vitesse > 5 and not valider_axe_vent(direction, spot_config["deco"]):
                    cause_heure = f"🧭 Vent de travers ({direction})"
                    facteurs_limitants.add("🧭 Vent arrière ou travers")
                    heure_bloquee = True

                if heure_bloquee:
                    historique_vents.append(f"• {heure_texte} : {cause_heure}")
                else:
                    heures_valides_int.append(heure_int)
                    data_par_heure[heure_int] = {"vitesse": vitesse, "indice": indice_agitation}

            liste_fenetres = formater_fenetres(heures_valides_int, data_par_heure)
            if liste_fenetres:
                st.success("🟢 FEU VERT POUR LE VOL")
                for f in liste_fenetres: st.write(f)
            else:
                st.error("🛑 FEU ROUGE : RESTE AU SOL")
                for cause in facteurs_limitants: st.write(f"• {cause}")
                
            if historique_vents:
                st.markdown("**Détail horaire :**")
                for h_hist in historique_vents: st.write(h_hist)
        else:
            st.warning("Impossible de récupérer les prévisions Open-Meteo.")

with col_droite:
    st.subheader("Guide des Règles")
    st.markdown("""
    - **Débutant (<20 ploufs) :** Max 15 km/h | Agitation Max 6/10.
    - **Progression (20-40 ploufs) :** Max 20 km/h | Agitation Max 8/10.
    - **Confirmé (>40 ploufs) :** Max 26 km/h | Agitation Max 10/10.
    """)
    
    st.markdown("---")
    st.subheader("📌 Spécificités")
    st.write(spot_config["conseil_site"])
    st.write(f"• **Déco :** {', '.join(spot_config['deco'])}")
    
    ffvl_id = spot_config.get("balise_ffvl_id")
    if ffvl_id:
        st.markdown("---")
        st.subheader("📡 Relevé BaliseMétéo")
        
        balise_reelle = recuperer_donnees_balise_reelles(ffvl_id)
        
        st.write(f"• **Heure du relevé :** {balise_reelle['heure']}")
        st.write(f"• **Vent moyen :** {balise_reelle['vent_moyen']} km/h")
        st.write(f"• **Vent max :** {balise_reelle['vent_max']} km/h")
        st.write(f"• **Indice d'agitation :** {balise_reelle['indice']}/10")
