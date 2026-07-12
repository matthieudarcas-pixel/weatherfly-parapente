import tkinter as tk
from tkinter import ttk, messagebox
import requests
from datetime import datetime, timedelta

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

class WeatherFlyApp:
    def __init__(self, root):
        self.root = root
        self.root.title("WeatherFly - Assistant Vol Libre")
        self.root.minsize(850, 650)
        
        # Variables de l'interface
        self.spot_var = tk.StringVar(value=list(SPOTS.keys())[0])
        self.date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        self.ploufs_var = tk.StringVar(value="15")
        
        self.m_oreilles = tk.BooleanVar(value=False)
        self.m_face = tk.BooleanVar(value=False)
        
        self.create_widgets()

    def create_widgets(self):
        # Configuration de la grille principale de la fenêtre racine
        self.root.columnconfigure(0, weight=3, uniform="col")
        self.root.columnconfigure(1, weight=2, uniform="col")
        self.root.rowconfigure(0, weight=1)
        
        # --- COLONNE GAUCHE ---
        frame_gauche = ttk.Frame(self.root, padding=10)
        frame_gauche.grid(row=0, column=0, sticky="nsew")
        frame_gauche.rowconfigure(1, weight=1)  # Permet au cadre résultats de s'étirer verticalement
        frame_gauche.columnconfigure(0, weight=1)
        
        # Cadre configuration
        frame_config = ttk.LabelFrame(frame_gauche, text=" Configuration Pilote & Spot ", padding=10)
        frame_config.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        frame_config.columnconfigure(1, weight=1)
        
        ttk.Label(frame_config, text="Spot :").grid(row=0, column=0, sticky="w", pady=3)
        cb_spots = ttk.Combobox(frame_config, textvariable=self.spot_var, values=list(SPOTS.keys()), state="readonly")
        cb_spots.grid(row=0, column=1, sticky="ew", pady=3, padx=5)
        
        ttk.Label(frame_config, text="Date du vol :").grid(row=1, column=0, sticky="w", pady=3)
        dates_possibles = [(datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(15)]
        cb_dates = ttk.Combobox(frame_config, textvariable=self.date_var, values=dates_possibles, state="readonly")
        cb_dates.grid(row=1, column=1, sticky="ew", pady=3, padx=5)
        
        ttk.Label(frame_config, text="Expérience (Nb de ploufs) :").grid(row=2, column=0, sticky="w", pady=3)
        ent_ploufs = ttk.Entry(frame_config, textvariable=self.ploufs_var)
        ent_ploufs.grid(row=2, column=1, sticky="ew", pady=3, padx=5)
        
        ttk.Label(frame_config, text="Manœuvres maîtrisées :").grid(row=3, column=0, sticky="w", pady=3)
        frame_chk = ttk.Frame(frame_config)
        frame_chk.grid(row=3, column=1, sticky="w", pady=3)
        ttk.Checkbutton(frame_chk, text="Oreilles", variable=self.m_oreilles).pack(side="left", padx=2)
        ttk.Checkbutton(frame_chk, text="Face voile (>15km/h)", variable=self.m_face).pack(side="left", padx=2)
        
        btn_analyser = ttk.Button(frame_config, text="RECHERCHER ET ANALYSER", command=self.analyser_vol)
        btn_analyser.grid(row=4, column=0, columnspan=2, sticky="ew", padx=5, pady=8)
        
        # Cadre résultats
        frame_res = ttk.LabelFrame(frame_gauche, text=" Verdict Météo & Aérologie ", padding=10)
        frame_res.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        frame_res.rowconfigure(1, weight=1)
        frame_res.columnconfigure(0, weight=1)
        
        self.badge_status = tk.Label(frame_res, text="EN ATTENTE D'ANALYSE", font=("Arial", 10, "bold"), bg="#f3f4f6", fg="#374151", pady=4)
        self.badge_status.grid(row=0, column=0, sticky="ew", pady=3)
        
        self.txt_output = tk.Text(frame_res, wrap="word", height=15)
        self.txt_output.grid(row=1, column=0, sticky="nsew", pady=3)
        self.txt_output.config(state="disabled")
        
        # --- COLONNE DROITE (Guide des Règles Intégrées) ---
        frame_droite = ttk.LabelFrame(self.root, text=" Guide des Règles Intégrées ", padding=10)
        frame_droite.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        
        regles_contenu = (
            "LIMITES DE VENT (MÉTÉO)\n"
            "• <20 ploufs (Débutant) : Max 15 km/h\n"
            "• 20 à 40 ploufs (Progression) : Max 20 km/h\n"
            "• >40 ploufs (Confirmé) : Max 26 km/h\n\n"
            "ACTIVITÉ THERMIQUE (AGITATION)\n"
            "• Débutant (<20 ploufs) :\n"
            "  ❌ Agitation max autorisée : 6/10\n"
            "• Progression (20 à 40 ploufs) :\n"
            "  ❌ Agitation max autorisée : 8/10\n"
            "  ❌ Indice ≥8 interdit SAUF si oreilles cochées\n"
            "• Confirmé (>40 ploufs) :\n"
            "  ✔️ Aucune restriction d'indice\n\n"
            "TECHNIQUE ET PILOTAGE\n"
            "• Si Vent > 15 km/h : Gonflage face voile obligatoire\n"
            "• Si Oreilles non maîtrisées et Indice ≥ 8 : Blocage pic thermique\n\n"
            "TOLÉRANCE D'ORIENTATION\n"
            "• Axe du vent toléré jusqu'à 45° max du déco\n"
            "• Au-delà de 5 km/h de vent, tout axe hors plage invalide l'heure\n\n"
            "RÈGLES PARTICULIÈRES SITES\n"
            "• Port de Lers : Vent Sud (S, SO, SE) > 10 km/h = DANGER\n"
            "• Précipitations > 0.1 mm = Vol interdit"
        )
        lbl_guide = ttk.Label(frame_droite, text=regles_contenu, font=("Arial", 8), justify="left", foreground="#374151")
        lbl_guide.pack(fill="both", expand=True)

    def convertir_degres_en_direction(self, degres):
        if (degres >= 337.5) or (degres < 22.5): return "N"
        if 22.5 <= degres < 67.5: return "NE"
        if 67.5 <= degres < 112.5: return "E"
        if 112.5 <= degres < 157.5: return "SE"
        if 157.5 <= degres < 202.5: return "S"
        if 202.5 <= degres < 247.5: return "SO"
        if 247.5 <= degres < 292.5: return "O"
        return "NO"

    def valider_axe_vent(self, direction_vent, direction_deco):
        angle_vent = COMPASS_ANGLES[direction_vent]
        angle_deco = COMPASS_ANGLES[direction_deco]
        ecart = abs(angle_vent - angle_deco)
        if ecart > 180: ecart = 360 - ecart
        return ecart <= 45

    def formater_fenetres(self, heures_valides, data_par_heure):
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

    def recuperer_vraie_meteo(self, lat, lon, date_str):
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&start_date={date_str}&end_date={date_str}&hourly=temperature_2m,wind_speed_10m,wind_gusts_10m,wind_direction_10m,precipitation,cape&wind_speed_unit=kmh&timezone=Europe%2FParis"
        try:
            resp = requests.get(url, timeout=5)
            return resp.json().get("hourly", {})
        except Exception as e:
            messagebox.showerror("Erreur Réseau", f"Impossible de joindre l'API météo : {e}")
            return {}

    def analyser_vol(self):
        spot_name = self.spot_var.get()
        spot_config = SPOTS[spot_name]
        date_selectionnee = self.date_var.get()
        
        try:
            ploufs = int(self.ploufs_var.get())
        except ValueError:
            messagebox.showerror("Erreur", "Nombre de ploufs invalide !")
            return

        hourly_data = self.recuperer_vraie_meteo(spot_config["lat"], spot_config["lon"], date_selectionnee)
        if not hourly_data or "time" not in hourly_data: return

        heures_valides_int = []
        data_par_heure = {}  
        facteurs_limitants = set()
        historique_vents = []
        
        vent_max_autorise = 15 if ploufs < 20 else (20 if ploufs <= 40 else 26)
        
        # --- SEUILS MODIFIÉS (Débutant 0-6, Intermédiaire/Progression 0-8) ---
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
            direction = self.convertir_degres_en_direction(hourly_data["wind_direction_10m"][i])
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
            elif not self.m_oreilles.get() and indice_agitation >= seuil_agitation_max:
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
            elif vitesse > 15 and not self.m_face.get():
                cause_heure = f"🛑 Face voile requis ({vitesse} km/h)"
                facteurs_limitants.add("🛑 Face voile requis mais non coché (Vent > 15km/h)")
                heure_bloquee = True
            elif vitesse > 5 and not self.valider_axe_vent(direction, spot_config["deco"]):
                cause_heure = f"🧭 Vent de travers/cul ({vitesse} km/h {direction})"
                facteurs_limitants.add(f"🧭 Vent arrière ou travers (Déco orienté {spot_config['deco']})")
                heure_bloquee = True

            if heure_bloquee:
                historique_vents.append(f"• {heure_texte} : {cause_heure}")
            else:
                heures_valides_int.append(heure_int)
                data_par_heure[heure_int] = {"vitesse": vitesse, "indice": indice_agitation}

        self.txt_output.config(state="normal")
        self.txt_output.delete("1.0", tk.END)

        liste_fenetres = self.formater_fenetres(heures_valides_int, data_par_heure)

        if liste_fenetres:
            self.badge_status.config(text="🟢 FEU VERT POUR LE VOL", bg="#dcfce7", fg="#15803d")
            texte_final = (
                f"📅 Date : {date_selectionnee}\n"
                f"👤 Profil : {profil} ({ploufs} ploufs) - Seuil agitation max : {seuil_agitation_max}/10\n\n"
                f"✅ FENÊTRE(S) DE VOL COMPATIBLE(S) :\n" + "\n".join(liste_fenetres) + "\n\n"
            )
            if historique_vents:
                texte_final += "🔄 CRÉNEAUX NON VALIDÉS / HORS LIMITES :\n" + "\n".join(historique_vents[:6]) + "\n\n"
            texte_final += f"💡 CONSEIL DU SITE :\n{spot_config['conseil_site']}\n"
        else:
            self.badge_status.config(text="🛑 FEU ROUGE : RESTE AU SOL", bg="#fee2e2", fg="#b91c1c")
            liste_causes = "\n".join([f"• {cause}" for cause in facteurs_limitants])
            texte_final = (
                f"📅 Date : {date_selectionnee}\n"
                f"👤 Profil : {profil} (Seuil agitation max : {seuil_agitation_max}/10)\n\n"
                f"❌ FACTEURS BLOQUANTS CONSTATÉS :\n{liste_causes}\n\n"
            )
            if historique_vents:
                texte_final += "🔄 DÉTAIL DES HEURES DU JOUR :\n" + "\n".join(historique_vents[:6]) + "\n"

        self.txt_output.insert(tk.END, texte_final)
        self.txt_output.config(state="disabled")

if __name__ == "__main__":
    root = tk.Tk()
    app = WeatherFlyApp(root)
    root.mainloop()
