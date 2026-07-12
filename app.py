import streamlit as st
import requests
from datetime import datetime, timedelta

# --- CONFIGURATION DES SPOTS ---
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
    if ecart > 180:
        ecart = 360 - ecart
    return ecart <= 45

def formater_fenetres(heures_valides, vents_par_heure):
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
        vitesses = [vents_par_heure[h] for h in bloc]
        v_min = min(vitesses)
        v_max = max(vitesses)
        fourchette = f"{v_min} km/h" if v_min == v_max else f"{v_min}-{v_max} km/h"
        
        if h_debut == h_fin:
            resultats_txt.append(f"• **{h_debut}:00 à {h_debut+1}:00** (Vent : {fourchette}) _[Créneau court]_")
        else:
            resultats_txt.append(f"• **{h_debut}:00 à {h_fin+1}:00** (Vent : {fourchette})")
    return resultats_txt

# --- INTERFACE WEB STREAMLIT ---
st.set_page_config(page_title="WeatherFly - Vol Libre", page_icon="🪂", layout="wide")

st.title("🪂 WeatherFly Live")
st.caption("Analyseur météo et Guide des Règles de Sécurité")

col_gauche, col_droite = st.columns([2, 1])

with col_gauche:
    st.subheader("📊 Configuration Pilote & Spot")
    spot_name = st.selectbox("📍 Choisir le Spot :", list(SPOTS.keys()))
    
    dates_possibles = [(datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(15)]
    date_selectionnee = st.selectbox("📅 Date du vol :", dates_possibles)
    
    ploufs = st.number_input("🪂 Expérience (Nombre de ploufs) :", min_value=0, max_value=5000, value=15)
    
    st.write("🛠️ **Manœuvres maîtrisées :**")
    m_oreilles = st.checkbox("Oreilles maîtrisées")
    m_face = st.checkbox("Gonflage face voile maîtrisé (>15km/h)")
    
    Bouton_analyser = st.button("📡 RECHERCHER ET ANALYSER", type="primary", use_container_width=True)

with col_droite:
    st.subheader("📘 Règles Intégrées")
    st.info(
        "**LIMITES DE VENT (MÉTÉO)**\n"
        "- < 20 ploufs (Débutant) : Max 15 km/h\n"
        "- 20 à 40 ploufs (Progression) : Max 20 km/h\n"
        "- > 40 ploufs (Confirmé) : Max 26 km/h\n\n"
        "**ACTIVITÉ THERMIQUE (HORAIRES)**\n"
        "- Débutant (< 20 ploufs) : ❌ Interdit 12h30-16h30\n"
        "- Progression (20-40 ploufs) : ❌ Interdit 13h30-15h30 (Total)\n"
        "- Confirmé (> 40 ploufs) : ✅ Pas de restriction horaire\n\n"
        "**TECHNIQUE**\n"
        "- Vent > 15 km/h : 🛑 Face voile obligatoire\n"
        "- Si Oreilles non maîtrisées : ❌ Blocage pic thermique (13h30-15h30) tous profils."
    )

if Bouton_analyser:
    st.divider()
    spot_config = SPOTS[spot_name]
    url = f"https://api.open-meteo.com/v1/forecast?latitude={spot_config['lat']}&longitude={spot_config['lon']}&start_date={date_selectionnee}&end_date={date_selectionnee}&hourly=temperature_2m,wind_speed_10m,wind_direction_10m,precipitation&wind_speed_unit=kmh&timezone=Europe%2FParis"
    
    try:
        response = requests.get(url, timeout=5)
        hourly_data = response.json()["hourly"]
        
        heures_valides_int = []
        vents_par_heure = {}  
        facteurs_limitants = set()
        historique_vents = []
        
        vent_max_autorise = 15 if ploufs < 20 else (20 if ploufs < 40 else 26)
        profil = "Débutant" if ploufs < 20 else ("Progression" if ploufs < 40 else "Confirmé")

        for i in range(len(hourly_data["time"])):
            heure_texte = hourly_data["time"][i].split("T")[1][:5]
            heure_int = int(heure_texte.split(":")[0])
            
            if heure_int < 8 or heure_int > 20: continue
                
            vitesse = round(hourly_data["wind_speed_10m"][i])
            direction = convertir_degres_en_direction(hourly_data["wind_direction_10m"][i])
            pluie = hourly_data["precipitation"][i]

            heure_bloquee = False
            cause_heure = ""

            if profil == "Débutant" and (12 <= heure_int <= 16):
                cause_heure = f"☀️ Fort thermique ({vitesse} km/h)"
                facteurs_limitants.add("☀️ Activité thermique trop forte (Débutant : 12h30-16h30)")
                heure_bloquee = True
            elif profil == "Progression" and (13 <= heure_int <= 15):
                cause_heure = f"☀️ Interdiction absolue Niveau Progression ({vitesse} km/h)"
                facteurs_limitants.add("☀️ Fenêtre 13h30-15h30 strictly interdite en niveau Progression")
                heure_bloquee = True
            elif not m_oreilles and (13 <= heure_int <= 15):
                cause_heure = f"🔥 Pic thermique (Oreilles requises | {vitesse} km/h)"
                facteurs_limitants.add("🔥 Pic thermique (13h30-15h30) nécessitant la maîtrise des oreilles")
                heure_bloquee = True

            if heure_bloquee:
                historique_vents.append(f"- **{heure_texte}** : {cause_heure}")
                continue

            if spot_config["interdit_sud"] and direction in ["S", "SO", "SE"] and vitesse > 10:
                cause_heure = f"⚠️ Danger Sud ({vitesse} km/h {direction})"
                facteurs_limitants.add("⚠️ Danger Vent de Sud (Risque de Foehn / Rouleaux)")
                heure_bloquee = True
            elif pluie > 0.1: 
                cause_heure = f"🌧️ Pluie ({vitesse} km/h)"
                facteurs_limitants.add("🌧️ Présence de pluie")
                heure_bloquee = True
            elif vitesse > vent_max_autorise:
                cause_heure = f"💨 Trop fort ({vitesse} km/h)"
                facteurs_limitants.add(f"💨 Vent trop fort pour ton niveau {profil} (>{vent_max_autorise}km/h)")
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
                historique_vents.append(f"- **{heure_texte}** : {cause_heure}")
            else:
                heures_valides_int.append(heure_int)
                vents_par_heure[heure_int] = vitesse

        liste_fenetres = formater_fenetres(heures_valides_int, vents_par_heure)

        if liste_fenetres:
            st.success("🟢 FEU VERT POUR LE VOL")
            st.write(f"**Profil détecté :** {profil} ({ploufs} ploufs)")
            st.markdown("### ✅ Fenêtre(s) de vol compatible(s) :")
            for f in liste_fenetres:
                st.markdown(f)
            
            with st.expander("🔄 Voir le détail des heures rejetées"):
                for h in historique_vents:
                    st.markdown(h)
        else:
            st.error("🛑 FEU ROUGE : RESTE AU SOL")
            st.markdown("### ❌ Facteurs bloquants constatés :")
            for cause in facteurs_limitants:
                st.markdown(f"- {cause}")
                
            with st.expander("🔄 Voir le détail heure par heure"):
                for h in historique_vents:
                    st.markdown(h)
                    
        st.warning(f"💡 **Conseil du site :** {spot_config['conseil_site']}")

    except Exception as e:
        st.error(f"Erreur de connexion à l'API météo : {e}")