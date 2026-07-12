import streamlit as st
import requests
from datetime import datetime, timedelta

# --- CONFIGURATION DE LA PAGE STREAMLIT ---
st.set_page_config(page_title="WeatherFly - Assistant Vol Libre", layout="wide")

# --- CONFIGURATION DES SPOTS LOCAUX ---
SPOTS = {
    "Port de Lers (09)": {
        "lat": 42.8036, 
        "lon": 1.3711, 
        "deco": "NO",  
        "interdit_sud": True,
        "conseil_site": "⚠️ Le Port de Lers peut forcir très vite en thermique. Reste vigilant aux cycles."
    },
    "Moulis (09)": {
        "lat": 42.9564, 
        "lon": 1.0903, 
        "deco": "N",   
        "interdit_sud": False,
        "conseil_site": "Brise de vallée classique. Attention au vent météo d'Ouest qui peut culer au déco."
    },
    "Gensac (31)": {
        "lat": 43.2107, 
        "lon": 1.1312, 
        "deco": "O",   
        "interdit_sud": False,
        "conseil_site": "Vol de plaine. Idéal en dynamique par vent d'Ouest modéré."
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

def valider_axe_vent(direction_vent, direction_deco):
    angle_vent = COMPASS_ANGLES[direction_vent]
    angle_deco = COMPASS_ANGLES[direction_deco]
    ecart = abs(angle_vent - angle_deco)
    if ecart > 180: ecart = 360 - ecart
    return ecart <= 45

def formater_fenetres(heures_valides, data_par_heure):
    if not heures_valides: return []
    precedent = heures_valides[0]
    blocs = []
    courant = [heures_valides[0]]
    
    for h in heures_valides[1:]:
        if h == precedent + 1:
            courant.append(h)
            precedent = h
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
        resp = requests.get(url, timeout=15)
        return resp.json().get("hourly", {})
    except Exception as e:
        st.error(f"Impossible de joindre l'API météo : {e}")
        return {}

# --- INTERFACE UTILISATEUR (STREAMLIT) ---
st.title("WeatherFly - Assistant Vol Libre")

col_gauche, col_droite = st.columns([3, 2])

with col_gauche:
    st.subheader("Configuration Pilote & Spot")
    spot_name = st.selectbox("Spot :", list(SPOTS.keys()))
    spot_config = SPOTS[spot_name]
    
    dates_possibles = [(datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(15)]
    date_selectionnee = st.selectbox("Date du vol :", dates_possibles)
    
    ploufs = st.number_input("Expérience (Nb de ploufs) :", min_value=0, max_value=1000, value=15)
    
    col_chk1, col_chk2 = st.columns(2)
    with col_chk1:
        m_oreilles = st.checkbox("Oreilles")
    with col_chk2:
        m_face = st.checkbox("Face voile (>15km/h)")
        
    analyser_clic = st.button("RECHERCHER ET ANALYSER", type="primary")

    st.subheader("Verdict Météo & Aérologie")
    
    if analyser_clic:
        hourly_data = recuperer_vraie_meteo(spot_config["lat"], spot_config["lon"], date_selectionnee)
        
        if hourly_data and "time" in hourly_data:
            heures_valides_int = []
            data_par_heure = {}  
            facteurs_limitants = set()
            historique_vents = []
            
            vent_max_autorise = 15 if ploufs < 20 else (20 if ploufs <= 40 else 26)
            
            if ploufs < 20:
                profil = "Débutant"
                seuil_agitation_max = 6
            elif ploufs <= 40:
                profil = "Progression"
                seuil_agitation_max = 8
            else:
                profil = "Confirmé"
                seuil_agitation_max = 10

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
                    cause_heure = f"☀️ Agitation thermique (Indice {indice_agitation}/10 > max {seuil_agitation_max} pour {profil})"
                    facteurs_limitants.add(f"☀️ Aérologie trop agitée (Indice {indice_agitation}/10 non adapté au niveau {profil})")
                    heure_bloquee = True
                elif not m_oreilles and indice_agitation >= 8:
                    cause_heure = f"🔥 Thermique marqué sans oreilles (Indice {indice_agitation}/10)"
                    facteurs_limitants.add("🔥 Pic thermique nécessitant la maîtrise des oreilles")
                    heure_bloquee = True

                if heure_bloquee:
                    historique_vents.append(f"• {heure_texte} : {cause_heure}")
                    continue

                if spot_config["interdit_sud"] and direction in ["S", "SO", "SE"] and vitesse > 10:
                    cause_heure = f"⚠️ Danger Sud ({vitesse} km/h {direction})"
                    facteurs_limitants.add("⚠️ Danger Vent de Sud (Risque de Foehn / Rouleaux)")
                    heure_bloquee = True
                elif pluie > 0.1: 
                    cause_heure = f"🌧️ Pluie ({vitesse} km/h)"
                    facteurs_limitants.add("🌧️ Présence de précipitations > 0.1 mm")
                    heure_bloquee = True
                elif vitesse > vent_max_autorise:
                    cause_heure = f"💨 Trop fort ({vitesse} km/h)"
                    facteurs_limitants.add(f"💨 Vent trop fort pour niveau {profil} (>{vent_max_autorise}km/h)")
                    heure_bloquee = True
                elif vitesse > 15 and not m_face:
                    cause_heure = f"🛑 Face voile requis ({vitesse} km/h)"
                    facteurs_limitants.add("🛑 Face voile requis mais non coché (Vent > 15km/h)")
                    heure_bloquee = True
                elif vitesse > 5 and not valider_axe_vent(direction, spot_config["deco"]):
                    cause_heure = f"🧭 Vent de travers/cul ({vitesse} km/h {direction})"
                    facteurs_limitants.add(f"🧭 Vent arrière ou travers (Déco orienté {spot_config['deco']})")
                    heure_bloquee = True

                if heure_bloquee:
                    historique_vents.append(f"• {heure_texte} : {cause_heure}")
                else:
                    heures_valides_int.append(heure_int)
                    data_par_heure[heure_int] = {"vitesse": vitesse, "indice": indice_agitation}

            liste_fenetres = formater_fenetres(heures_valides_int, data_par_heure)

            if liste_fenetres:
                st.success("🟢 FEU VERT POUR LE VOL")
                st.write(f"**Date :** {date_selectionnee}")
                st.write(f"**Profil :** {profil} ({ploufs} ploufs) - Seuil agitation max : {seuil_agitation_max}/10")
                st.markdown("**✅ FENÊTRE(S) DE VOL COMPATIBLE(S) :**")
                for f in liste_fenetres:
                    st.write(f)
                if historique_vents:
                    st.markdown("**🔄 CRÉNEAUX NON VALIDÉS / HORS LIMITES :**")
                    for h_v in historique_vents[:6]:
                        st.write(h_v)
                st.info(f"**💡 CONSEIL DU SITE :**\n{spot_config['conseil_site']}")
            else:
                st.error("🛑 FEU ROUGE : RESTE AU SOL")
                st.write(f"**Date :** {date_selectionnee}")
                st.write(f"**Profil :** {profil} (Seuil agitation max : {seuil_agitation_max}/10)")
                st.markdown("**❌ FACTEURS BLOQUANTS CONSTATÉS :**")
                for cause in facteurs_limitants:
                    st.write(f"• {cause}")
                if historique_vents:
                    st.markdown("**🔄 DÉTAIL DES HEURES DU JOUR :**")
                    for h_v in historique_vents[:6]:
                        st.write(h_v)
    else:
        st.info("Clique sur 'RECHERCHER ET ANALYSER' pour afficher le verdict.")

with col_droite:
    st.subheader("Guide des Règles Intégrées")
    regles_contenu = """
    **LIMITES DE VENT (MÉTÉO)**
    • <20 ploufs (Débutant) : Max 15 km/h
    • 20 à 40 ploufs (Progression) : Max 20 km/h
    • >40 ploufs (Confirmé) : Max 26 km/h

    **ACTIVITÉ THERMIQUE (AGITATION)**
    • Débutant (<20 ploufs) :
      ❌ Agitation max autorisée : 6/10
    • Progression (20 à 40 ploufs) :
      ❌ Agitation max autorisée : 8/10
      ❌ Indice ≥8 interdit SAUF si oreilles cochées
    • Confirmé (>40 ploufs) :
      ✔️ Aucune restriction d'indice

    **TECHNIQUE ET PILOTAGE**
    • Si Vent > 15 km/h : Gonflage face voile obligatoire
    • Si Oreilles non maîtrisées et Indice ≥ 8 : Blocage pic thermique

    **TOLÉRANCE D'ORIENTATION**
    • Axe du vent toléré jusqu'à 45° max du déco
    • Au-delà de 5 km/h de vent, tout axe hors plage invalide l'heure

    **RÈGLES PARTICULIÈRES SITES**
    • Port de Lers : Vent Sud (S, SO, SE) > 10 km/h = DANGER
    • Précipitations > 0.1 mm = Vol interdit
    """
    st.markdown(regles_contenu)
