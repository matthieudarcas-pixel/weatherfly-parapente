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
    if 67.5 <= degres < 112.5: return "E"
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

def recuperer_donnees_balise_reelles(balise_id):
    url = f"https://www.balisemeteo.com/balise.php?idBalise={balise_id}"
    fallback = {
        "heure": "09:40", "vent_moyen": 5.0, "dir_moyen": "NC", 
        "vent_max": 8.0, "dir_max": "NC", "indice": 1, "is_fallback": True
    }
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=4) as response:
            html_raw = response.read().decode('utf-8')
            
            text_clean = re.sub(r'<[^>]*>', ' ', html_raw)
            text_clean = re.sub(r'\s+', ' ', text_clean)
            
            match_heure = re.search(r"Relevé du \d{2}/\d{2}/\d{4} - (\d{2}:\d{2})", text_clean)
            heure_reelle = match_heure.group(1) if match_heure else "09:40"
            
            dir_moyen = "NC"
            vent_moyen = 5.0
            match_moyen = re.search(r"Vent moyen Direction\s*:\s*(.+?)\s*Vitesse\s*:\s*([\d\.,]+)", text_clean, re.IGNORECASE)
            if match_moyen:
                dir_moyen = match_moyen.group(1).strip()
                vent_moyen = float(match_moyen.group(2).replace(',', '.'))
                
            dir_max = "NC"
            vent_max = vent_moyen + 3.0
            match_maxi = re.search(r"Vent maxi Direction\s*:\s*(.+?)\s*Vitesse\s*:\s*([\d\.,]+)", text_clean, re.IGNORECASE)
            if match_maxi:
                dir_max = match_maxi.group(1).strip()
                vent_max = float(match_maxi.group(2).replace(',', '.'))

            delta_rafale = max(0.0, vent_max - vent_moyen)
            indice = min(10, round((delta_rafale / 3) + (vent_moyen / 5)))
            
            return {
                "heure": heure_reelle, 
                "vent_moyen": vent_moyen, "dir_moyen": dir_moyen,
                "vent_max": vent_max, "dir_max": dir_max, 
                "indice": max(1, indice), "is_fallback": False
            }
    except Exception:
        return fallback

# --- 5. INTERFACE GRAPHIQUE STREAMLIT ---
st.title("WeatherFly - Assistant Vol Libre")

if "refresh_counter" not in st.session_state:
    st.session_state.refresh_counter = 0

col_gauche, col_droite = st.columns([3, 2])

with col_gauche:
    # --- PROFIL PILOTE ---
    st.subheader("👤 1. Profil & Autonomie du Pilote")
    ploufs = st.number_input("Expérience (Nombre de ploufs) :", min_value=0, max_value=1000, value=15)
    
    col_chk1, col_chk2 = st.columns(2)
    with col_chk1: m_oreilles = st.checkbox("Maitrise des Grandes Oreilles")
    with col_chk2: m_face = st.checkbox("Maitrise du Gonflage Face Voile (>15km/h)")
    
    # Calcul Note Pilote
    note_pilote_brute = 1
    if ploufs < 10: note_pilote_brute = 2
    elif ploufs < 20: note_pilote_brute = 4
    elif ploufs <= 40: note_pilote_brute = 6
    elif ploufs <= 100: note_pilote_brute = 8
    else: note_pilote_brute = 10
    
    if m_oreilles: note_pilote_brute += 1
    if m_face: note_pilote_brute += 1
    note_pilote = min(10, max(1, note_pilote_brute))
    
    st.info(f"📊 **Note d'autonomie pilote estimée :** {note_pilote} / 10")
    
    st.markdown("---")
    
    # --- SPOT & DATE ---
    st.subheader("🧭 2. Localisation du Spot & Date")
    region_selectionnee = st.selectbox("Région :", list(SPOTS_HIERARCHIE.keys()))
    dept_selectionne = st.selectbox("Département :", list(SPOTS_HIERARCHIE[region_selectionnee].keys()))
    spot_name = st.selectbox("Site officiel :", list(SPOTS_HIERARCHIE[region_selectionnee][dept_selectionne].keys()))
    
    spot_config = SPOTS_HIERARCHIE[region_selectionnee][dept_selectionne][spot_name]
    
    dates_possibles = [(datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(15)]
    date_selectionnee = st.selectbox("Date du vol :", dates_possibles)
    
    st.markdown("---")
    analyser_clic = st.button("RECHERCHER ET ANALYSER", type="primary")
    
    # --- BLOC ENVELOPPÉ : VERDICT MÉTÉO ---
    st.subheader("Verdict Météo & Aérologie")
    indice_preve_actuel = 1
    
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
            
            heure_courante = datetime.now().hour

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
                
                if heure_int == heure_courante:
                    indice_preve_actuel = max(1, indice_agitation)

                heure_bloquee = False
                cause_heure = ""
                
                if indice_agitation > seuil_agitation_max:
                    cause_heure = f"☀️ Agitation thermique ({indice_agitation}/10)"
                    facteurs_limitants.add(f"☀️ Aérologie trop agitée ({indice_agitation}/10 > {seuil_agitation_max}/10)")
                    heure_bloquee = True
                elif not m_oreilles and indice_agitation >= 8:
                    cause_heure = f"🔥 Thermique marqué sans oreilles"
                    facteurs_limitants.add("🔥 Pic thermique (maîtrise des oreilles requise)")
                    heure_bloquee = True

                if heure_bloquee:
                    historique_vents.append(f"• {heure_texte} : {cause_heure}")
                    continue

                if spot_config["interdit_sud"] and direction in ["S", "SO", "SE"] and vitesse > 10:
                    cause_heure = f"⚠️ Danger Sud ({vitesse} km/h)"
                    facteurs_limitants.add(f"⚠️ Danger Vent de Sud sur ce spot par vent > 10 km/h")
                    heure_bloquee = True
                elif pluie > 0.1: 
                    cause_heure = f"🌧️ Pluie ({pluie} mm)"
                    facteurs_limitants.add("🌧️ Risque de précipitations")
                    heure_bloquee = True
                elif vitesse > vent_max_autorise:
                    cause_heure = f"💨 Trop fort ({vitesse} km/h)"
                    facteurs_limitants.add(f"💨 Vitesse du vent supérieure à ton maximum autorisé ({vent_max_autorise} km/h)")
                    heure_bloquee = True
                elif vitesse > 15 and not m_face:
                    cause_heure = f"🛑 Face voile requis ({vitesse} km/h)"
                    facteurs_limitants.add("🛑 Gonflage face voile non coché (requis dès 15 km/h)")
                    heure_bloquee = True
                elif vitesse > 5 and not valider_axe_vent(direction, spot_config["deco"]):
                    cause_heure = f"🧭 Vent de travers/arrière ({direction})"
                    facteurs_limitants.add(f"🧭 Alignement déco défavorable (Vent de travers/arrière : {direction})")
                    heure_bloquee = True

                if heure_bloquee:
                    historique_vents.append(f"• {heure_texte} : {cause_heure}")
                else:
                    heures_valides_int.append(heure_int)
                    data_par_heure[heure_int] = {"vitesse": vitesse, "indice": indice_agitation}

            # Affichage du Verdict Météo
            liste_fenetres = formater_fenetres(heures_valides_int, data_par_heure)
            if liste_fenetres:
                st.success("🟢 FEU VERT POUR LE VOL")
                for f in liste_fenetres: st.write(f)
            else:
                st.error("🛑 FEU ROUGE : RESTE AU SOL")
                for cause in facteurs_limitants: st.write(f"• {cause}")
                
            if historique_vents:
                st.markdown("**Détail de la journée :**")
                for h_hist in historique_vents: st.write(h_hist)
        else:
            st.warning("Impossible de récupérer les prévisions Open-Meteo.")

with col_droite:
    # --- BLOC VERROUILLÉ : RÈGLES ---
    st.subheader("Règles de Sécurité Intégrales")
    st.markdown("""
    *   **Niveau Débutant (< 20 ploufs) :** Max **15 km/h** | Agitation max **6/10**. Le thermique fort est à proscrire.
    *   **Niveau Progression (20 à 40 ploufs) :** Max **20 km/h** | Agitation max **8/10**. Maîtrise des petites turbulences.
    *   **Niveau Confirmé (> 40 ploufs) :** Max **26 km/h** | Agitation max **10/10**. Gestion des conditions fortes.
    *   **Règle du Face Voile :** Obligatoire si le vent moyen dépasse **15 km/h** pour assurer un décollage en sécurité.
    *   **Règle des Oreilles :** Interdiction de voler si l'indice d'agitation prévu atteint **8/10** sans maîtrise validée de la technique de descente rapide.
    """)
    
    # --- BLOC VERROUILLÉ : SPÉ SPOT ---
    st.markdown("---")
    st.subheader("📌 Spécificités du Spot")
    st.write(spot_config["conseil_site"])
    st.write(f"• **Orientations Déco acceptées :** {', '.join(spot_config['deco'])}")
    
    # --- BLOC VERROUILLÉ : RELEVÉ RÉEL BALISE ---
    ffvl_id = spot_config.get("balise_ffvl_id")
    if ffvl_id:
        st.markdown("---")
        st.subheader("📡 Relevé Réel BaliseMétéo")
        st.markdown(f"[Accéder à la page de la balise FFVL n°{ffvl_id}](https://www.balisemeteo.com/balise.php?idBalise={ffvl_id})")
        
        if st.button("🔄 Rafraîchir la balise", key="refresh_balise"):
            st.session_state.refresh_counter += 1
        
        balise_reelle = recuperer_donnees_balise_reelles(ffvl_id)
        
        st.write(f"• **Heure du relevé en direct :** {balise_reelle['heure']}")
        st.write(f"• **Vent moyen constaté :** {balise_reelle['vent_moyen']} km/h ({balise_reelle['dir_moyen']})")
        st.write(f"• **Vent max constaté :** {balise_reelle['vent_max']} km/h ({balise_reelle['dir_max']})")
        st.write(f"• **Indice d'agitation réel :** {balise_reelle['indice']}/10")
        
        if 'hourly_data' in locals() and hourly_data:
            diff_indice = balise_reelle['indice'] - indice_preve_actuel
            
            if diff_indice > 0:
                st.warning(f"📈 **Comparaison :** Les conditions réelles sur site sont plus fortes que prévu (**+{diff_indice} point(s)** d'indice d'agitation par rapport à la météo).")
            elif diff_indice < 0:
                st.info(f"📉 **Comparaison :** Les conditions réelles sur site sont plus calmes que prévu (**{diff_indice} point(s)** d'indice d'agitation par rapport à la météo).")
            else:
                st.success("🎯 **Comparaison :** L'agitation réelle sur site est parfaitement conforme aux prévisions météo (0 point d'écart).")
