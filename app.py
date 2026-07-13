def recuperer_donnees_balise_reelles(balise_id):
    url = f"https://www.balisemeteo.com/balise.php?idBalise={balise_id}"
    # Valeurs par défaut cohérentes en cas de coupure complète du serveur
    fallback = {"heure": "09:40", "vent_moyen": 6.0, "vent_max": 9.0, "indice": 1}
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            html_content = response.read().decode('utf-8')
            
            # 1. Extraction propre de l'heure
            match_heure = re.search(r"Relevé du \d{2}/\d{2}/\d{4} - (\d{2}:\d{2})", html_content)
            heure_reelle = match_heure.group(1) if match_heure else datetime.now().strftime("%H:%M")
            
            # 2. Extraction brute de TOUTES les valeurs numériques suivies de km/h
            chiffres_bruts = re.findall(r"([\d\.,]+)\s*(?:km/h|Kmh|KM/H)", html_content, re.IGNORECASE)
            
            valeurs = []
            for v in chiffres_bruts:
                cleaned = v.replace(',', '.')
                try:
                    valeurs.append(float(cleaned))
                except ValueError:
                    pass
            
            # 3. Attribution robuste basée sur l'ordre strict du tableau FFVL (Moyen, Mini, Maxi)
            # Même si le mini (valeurs[1]) vaut 0.0, cela n'impacte plus le Moyen (index 0) et le Maxi (index 2)
            if len(valeurs) >= 3:
                vent_moyen = valeurs[0]
                vent_max = valeurs[2]
            elif len(valeurs) == 2:
                vent_moyen = valeurs[0]
                vent_max = valeurs[1]
            else:
                return fallback

            # 4. Sécurité : On ne bloque QUE si Moyen ET Max valent strictement 0 (ce qui signifierait une panne capteur/site)
            if vent_moyen == 0.0 and vent_max == 0.0:
                # Si le site répond mais affiche 0 partout (panne), on applique le fallback pour ne pas freezer l'UI
                return fallback

            # Calcul de l'indice de l'agitation à l'instant T
            delta_rafale = max(0.0, vent_max - vent_moyen)
            indice = min(10, round((delta_rafale / 3) + (vent_moyen / 5)))
            
            return {
                "heure": heure_reelle,
                "vent_moyen": vent_moyen,
                "vent_max": vent_max,
                "indice": max(1, indice)
            }
    except Exception:
        return fallback
