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
                "pioupiou_id": "327",  # ID Pioupiou / OpenWindMap associé si dispo
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

@st.cache_data(ttl=300)
def recuperer_releve_pioupiou(pioupiou_id):
    """Interroge l'API live de Pioupiou / OpenWindMap pour récupérer le vent instantané."""
    if not pioupiou_id:
        return None
    url = f"https://api.pioupiou.fr/v1/live/{pioupiou_id}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=8) as response:
            res_json = json.loads(response.read().decode())
            return res_json.get("data", {})
    except Exception:
        return None

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
    with col_chk1:
        m_oreilles = st.checkbox("Oreilles", key="oreilles_chk")
    with col_chk2:
        m_face = st.checkbox("Face voile (>15km/h)", key="face_chk")
        
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
                    cause_heure = f"☀️ Agitation thermique (Indice {indice_agitation}/10 > max {seuil_agitation_max} for {profil})"
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
                    facteurs_limitants.add("⚠️ Danger Vent de Sud (Sensibilité spécifique du site > 10 km/h)")
                    heure_bloquee = True
                elif pluie > 0.1: 
                    cause_heure = f"🌧️ Pluie ({vitesse} km/h)"
                    facteurs_limitants.add("🌧️ Précipitations > 0.1 mm = Vol interdit")
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
                    facteurs_limitants.add(f"🧭 Vent arrière ou travers (Déco orienté {', '.join(spot_config['deco'])})")
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
                st.info(f"**💡 CONSEIL DU SITE ({spot_name} - Déco {', '.join(spot_config['deco'])}) :**\n{spot_config['conseil_site']}")
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
        st.info("Sélectionne ton spot dans les menus et clique sur 'RECHERCHER ET ANALYSER'.")

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
    • Axe du vent toléré jusqu'à 45° max de l'orientation du déco
    • Au-delà de 5 km/h de vent, tout axe hors plage invalide l'heure
    """
    st.markdown(regles_contenu)
    
    est_aujourdhui = (date_selectionnee == datetime.now().strftime("%Y-%m-%d"))
    if est_aujourdhui:
        st.markdown("---")
        st.subheader("📡 Relevé Pioupiou (En direct)")
        if spot_config.get("pioupiou_id"):
            releve_pp = recuperer_releve_pioupiou(spot_config["pioupiou_id"])
            if releve_pp:
                st.write(f"• **Vent moyen** : {releve_pp.get('wind_speed_avg', 'N/A')} km/h")
                st.write(f"• **Rafales** : {releve_pp.get('wind_speed_max', 'N/A')} km/h")
                st.write(f"• **Direction** : {releve_pp.get('wind_direction', 'N/A')}°")
            st.markdown(f"👉 [Consulter sur OpenWindMap](https://www.openwindmap.org/pioupiou-{spot_config.get('pioupiou_id')})")
        elif spot_config.get("balise_ffvl_id"):
            st.markdown(f"👉 [Consulter la balise sur BaliseMétéo](https://www.balisemeteo.com/balise.php?idBalise={spot_config.get('balise_ffvl_id')})")
        else:
            st.info("Aucune balise n'est associée à ce site.")
