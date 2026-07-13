def recuperer_donnees_balise_reelles(balise_id):
    url = f"https://www.balisemeteo.com/balise.php?idBalise={balise_id}"
    fallback = {"heure": "09:40", "vent_moyen": 6.0, "vent_max": 9.0, "indice": 1}
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=8) as response:
            html_content = response.read().decode('utf-8')
            
            match_heure = re.search(r"(\d{2}:\d{2})", html_content)
            heure_reelle = match_heure.group(1) if match_heure else "09:40"
            
            # Captures ultra-robustes traversant les retours à la ligne (.+?) jusqu'au premier chiffre après "Vitesse"
            match_moyen = re.search(r"Vent\s+moyen.+?Vitesse\s*:\s*([\d\.,]+)", html_content, re.DOTALL | re.IGNORECASE)
            match_maxi = re.search(r"Vent\s+maxi.+?Vitesse\s*:\s*([\d\.,]+)", html_content, re.DOTALL | re.IGNORECASE)
            
            if match_moyen and match_maxi:
                vent_moyen = float(match_moyen.group(1).replace(',', '.'))
                vent_max = float(match_maxi.group(1).replace(',', '.'))
            else:
                # Système de secours (recherche globale des km/h) si le texte changeait
                chiffres = re.findall(r"([\d\.,]+)\s*(?:km/h|Kmh)", html_content, re.IGNORECASE)
                valeurs = [float(v.replace(',', '.')) for v in chiffres if v.replace(',', '').isdigit()]
                if len(valeurs) >= 3:
                    vent_moyen = valeurs[0]
                    vent_max = valeurs[2] # Saute l'index 1 (le vent mini)
                elif len(valeurs) == 2:
                    vent_moyen = valeurs[0]
                    vent_max = valeurs[1]
                else:
                    return fallback

            if vent_moyen == 0.0 and vent_max == 0.0:
                return fallback

            delta_rafale = max(0.0, vent_max - vent_moyen)
            indice = min(10, round((delta_rafale / 3) + (vent_moyen / 5)))
            return {"heure": heure_reelle, "vent_moyen": vent_moyen, "vent_max": vent_max, "indice": max(1, indice)}
    except Exception:
        return fallback
    
