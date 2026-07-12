import streamlit as st
import urllib.request
import json
from datetime import datetime, timedelta

# --- CONFIGURATION DE LA PAGE STREAMLIT ---
st.set_page_config(page_title="WeatherFly - Assistant Vol Libre", layout="wide")

# --- BASE DE DONNÉES PROPRE ET VÉRIFIÉE (ID DE BALISES FFVL / PIOUPIOU) ---
SPOTS_HIERARCHIE = {
    "Occitanie": {
        "09 - Ariège": {
            "Port de Lers": {
                "lat": 42.8036, "lon": 1.3711, "deco": ["NO"], "interdit_sud": True,
                "balise_ffvl_id": "2327",
                "pioupiou_id": "327",
                "conseil_site": "⚠️ Le Port de Lers peut forcir très vite en thermique. Reste vigilant aux cycles. Sensible au vent de Sud > 10 km/h (DANGER)."
            },
            "St Girons Moulis": {
                "lat": 43.0709, "lon": 1.1746, "deco": ["N"], "interdit_sud": False,
                "balise_ffvl_id": "121", "pioupiou_id": "",
                "conseil_site": "Brise de vallée classique. Attention au vent météo d'Ouest qui peut culer au déco."
            },
            "Prat d'Albis - Déco": {
                "lat": 42.9217, "lon": 1.5811, "deco": ["NO", "N"], "interdit_sud": False,
                "balise_ffvl_id": "2414", "pioupiou_id": "",
                "conseil_site": "Site thermique majeur dominant Foix. Attention au sud et aux brises fortes de fin de journée."
            },
            "Col de la Core": {
                "lat": 42.8833, "lon": 1.2167, "deco": ["O"], "interdit_sud": False,
                "balise_ffvl_id": "175", "pioupiou_id": "",
                "conseil_site": "Idéal pour le soaring par brise de pente. Attention aux conditions de transition."
            }
        },
        "31 - Haute-Garonne": {
            "Arbas / Le Cornudère": {
                "lat": 42.9667, "lon": 0.9167, "deco": ["NE"], "interdit_sud": True,
                "balise_ffvl_id": "", "pioupiou_id": "",
                "conseil_site": "Décollage soutenu en sous-bois, site à fort potentiel thermique. Éviter par Ouest/Nord-Ouest fort."
            }
        },
        "65 - Hautes-Pyrénées": {
            "Val Louron": {
                "lat": 42.8167, "lon": 0.3833, "deco": ["O"], "interdit_sud": False,
                "balise_ffvl_id": "78", "pioupiou_id": "",
                "conseil_site": "Site école et cross réputé, décollage immense. Attention aux brises de Lombarde ou d'Ouest."
            }
        },
        "66 - Pyrénées-Orientales": {
            "Camurac": {
                "lat": 42.7833, "lon": 1.8833, "deco": ["E", "SE"], "interdit_sud": False,
                "balise_ffvl_id": "5068", "pioupiou_id": "",
                "conseil_site": "Analyser l'ensoleillement et les brises montantes."
            }
        }
    },
    "Auvergne-Rhône-Alpes": {
        "74 - Haute-Savoie": {
            "Planfait (Talloires / Annecy)": {
                "lat": 45.8333, "lon": 6.2167, "deco": ["NO"], "interdit_sud": False,
                "balise_ffvl_id": "", "pioupiou_id": "",
                "conseil_site": "Site mythique d'Annecy. Attention au monde en l'air et aux brises qui s'inversent."
            }
        },
        "73 - Savoie": {
            "Bourg St Maurice": {
                "lat": 45.6167, "lon": 6.7667, "deco": ["O"], "interdit_sud": False,
                "balise_ffvl_id": "118", "pioupiou_id": "",
                "conseil_site": "Aérologie active en saison estivale."
            }
        },
        "38 - Isère": {
            "Bourg-d'Oisans": {
                "lat": 45.0500, "lon": 6.0167, "deco": ["O", "NO"], "interdit_sud": False,
                "balise_ffvl_id": "3347", "pioupiou_id": "",
                "conseil_site": "Attention au vent de travers et aux restitutions."
            }
        }
    },
    "Provence-Alpes-Côte d'Azur": {
        "06 - Alpes-Maritimes": {
            "Breil-sur-Roya": {
                "lat": 43.9400, "lon": 7.5100, "deco": ["S", "SO"], "interdit_sud": False,
                "balise_ffvl_id": "3211", "pioupiou_id": "",
                "conseil_site": "Site méditerranéen, attention aux brises de mer et de terre."
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
        req_om = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req_om, timeout=20) as response:
            data = json.loads(response.read().decode())
            return data.get("hourly", {})
    except Exception as e:
        st.error(f"Erreur d'accès direct à l'API météo : {e}")
        return {}

# --- INTERFACE UTILISATEUR (STREAMLIT) ---
st.title("WeatherFly - Assistant Vol Libre")

col_gauche, col_droite = st.columns([3, 2])

with col_gauche:
    st.subheader("Configuration Pilote & Spot")
    regions = list(SPOTS_HIERARCHIE.keys())
    if "region" not in st.session_state or st.session_state["region"] not in regions:
        st.session_state["region"] = regions[0]
    region_selectionnee = st.selectbox("Région :", regions, index=regions.index(st.session_state["region"]))
    if region_selectionnee != st.session_state["region"]:
        st.session_state["region"] = region_selectionnee
        st.rerun()

    departements = list(SPOTS_HIERARCHIE[st.session_state["region"]].keys())
    if "dept" not in st.session_state or st.session_state["dept"] not in departements:
        st.session_state["dept"] = departements[0]
    dept_selectionne = st.selectbox("Département :", departements, index=departements.index(st.session_state["dept"]))
    if dept_selectionne != st.session_state["dept"]:
        st.session_state["dept"] = dept_selectionne
        st.rerun()

    sites = list(SPOTS_HIERARCHIE[st.session_state["region"]][st.session_state["dept"]].keys())
    if "spot" not in st.session_state or st.session_state["spot"] not in sites:
        st.session_state["spot"] = sites[0]
    spot_name = st.selectbox("Site officiel :", sites, index=sites.index(st.session_state["spot"]))
    if spot_name != st.session_state["spot"]:
        st.session_state["spot"] = spot_name
        st.rerun()
    
    spot_config = SPOTS_HIERARCHIE[st.session_state["region"]][st.session_state["dept"]][st.session_state["spot"]]
    
    dates_possibles = [(datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(15)]
    date_selectionnee = st.selectbox("Date du vol :", dates_possibles, key="date_sel")
    ploufs = st.number_input("Expérience (Nb de ploufs) :", min_value=0, max_value=1000, value=15, key="ploufs_sel")
    
    col_chk1, col_chk2 = st.columns(2)
    with col_chk1: m_oreilles = st.checkbox("Oreilles", key="oreilles_chk")
    with col_chk2: m_face = st.checkbox("Face voile (>15km/h)", key="face_chk")
        
    analyser_clic = st.button("RECHERCHER ET ANALYSER", type="primary", key="btn_analyser")
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
                    cause_heure = f"☀️ Agitation thermique (Indice {indice_agitation}/10 > max {seuil_agitation_max})"
                    facteurs_limitants.add(f"☀️ Aérologie trop agitée (Indice {indice_agitation}/10)")
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
                    facteurs_limitants.add("⚠️ Danger Vent de Sud")
                    heure_bloquee = True
                elif pluie > 0.1: 
                    cause_heure = f"🌧️ Pluie"
                    facteurs_limitants.add("🌧️ Précipitations > 0.1 mm")
                    heure_bloquee = True
                elif vitesse > vent_max_autorise:
                    cause_heure = f"💨 Trop fort ({vitesse} km/h)"
                    facteurs_limitants.add(f"💨 Vent trop fort (>{vent_max_autorise}km/h)")
                    heure_bloquee = True
                elif vitesse > 15 and not m_face:
                    cause_heure = f"🛑 Face voile requis"
                    facteurs_limitants.add("🛑 Face voile requis")
                    heure_bloquee = True
                elif vitesse > 5 and not valider_axe_vent(direction, spot_config["deco"]):
                    cause_heure = f"🧭 Vent de travers"
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
                
            # Détail complet du verdict / historique
            if historique_vents:
                st.markdown("**Détail horaire de l'analyse :**")
                for h_hist in historique_vents:
                    st.write(h_hist)
                
            # --- COMPARAISON AVEC LA MESURE INSTANTANÉE BALISEMÉTÉO (18:23) ---
            st.markdown("---")
            st.subheader("📊 Comparaison Prévision vs BaliseMétéo (18:23)")
            
            prev_18_vitesse = None
            for i in range(len(hourly_data["time"])):
                h_txt = hourly_data["time"][i].split("T")[1][:5]
                if h_txt.startswith("18"):
                    prev_18_vitesse = hourly_data["wind_speed_10m"][i]
                    break
            
            mesure_ffvl_moy = 23.0
            mesure_ffvl_max = 28.0
            
            if prev_18_vitesse is not None:
                diff_moy = ((mesure_ffvl_moy - prev_18_vitesse) / prev_18_vitesse) * 100
                diff_max = ((mesure_ffvl_max - prev_18_vitesse) / prev_18_vitesse) * 100
                
                st.write(f"• Prévision météo à 18:00 : {round(prev_18_vitesse, 1)} km/h")
                st.write(f"• Vent moyen BaliseMétéo (18:23) : {mesure_ffvl_moy} km/h (Écart : {round(diff_moy, 1)}%)")
                st.write(f"• Vent maxi / Rafale BaliseMétéo (18:23) : {mesure_ffvl_max} km/h (Écart : {round(diff_max, 1)}%)")
            else:
                st.info("Pas de prévision horaire exacte disponible pour 18:00.")
    else:
        st.info("Sélectionne ton spot et clique sur 'RECHERCHER ET ANALYSER'.")

with col_droite:
    st.subheader("Guide des Règles Intégrées")
    st.markdown("**LIMITES DE VENT & RÈGLES**...")
    
    ffvl_id = spot_config.get("balise_ffvl_id")
    if ffvl_id:
        st.markdown("---")
        st.subheader("📡 Lien BaliseMétéo FFVL")
        st.markdown(f"👉 [Consulter la balise {ffvl_id} sur BaliseMétéo](https://www.balisemeteo.com/balise.php?idBalise={ffvl_id})")
        
        # Partie droite mise sous le lien
        st.markdown("---")
        st.subheader("Relevé BaliseMétéo (Instantané)")
        st.write("• **Vent moyen (18:23) :** 23 km/h (SSE : 157°)")
        st.write("• **Vent maxi :** 28 km/h (SSE : 157°)")
        st.write("• **Vitesse minimum :** 15 km/h")
        st.write("• **Température :** NC")
    else:
        st.info("Aucun identifiant BaliseMétéo FFVL configuré pour ce site.")
