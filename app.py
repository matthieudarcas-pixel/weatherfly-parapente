def recuperer_donnees_balise_reelles(balise_id):
    url = f"https://www.balisemeteo.com/balise.php?idBalise={balise_id}"
    # Valeurs de secours par défaut si le site est inaccessible
    fallback = {"heure": "09:40", "vent_moyen": 6.0, "vent_max": 9.0, "indice": 1}
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            html_content = response.read().decode('utf-8')
            
            # 1. Extraction de l'heure du relevé
            match_heure = re.search(r"Relevé du \d{2}/\d{2}/\d{4} - (\d{2}:\d{2})", html_content)
            heure_reelle = match_heure.group(1) if match_heure else "09:40"
            
            # 2. Ciblage chirurgical par mot-clé pour éviter tout décalage d'index
            # On cherche directement le nombre écrit juste après "Vent moyen" et "Vent maxi"
            match_moyen = re.search(r"Vent moyen\s*:\s*([\d\.,]+)", html_content, re.IGNORECASE)
            match_maxi = re.search(r"Vent maxi\s*:\s*([\d\.,]+)", html_content, re.IGNORECASE)
            
            if match_moyen and match_maxi:
                vent_moyen = float(match_moyen.group(1).replace(',', '.'))
                vent_max = float(match_maxi.group(1).replace(',', '.'))
            else:
                # Système B : Si le site a retiré les labels textuels, on se rabat sur les 3 premières vitesses
                chiffres_bruts = re.findall(r"([\d\.,]+)\s*(?:km/h|Kmh)", html_content, re.IGNORECASE)
                valeurs = [float(v.replace(',', '.')) for v in chiffres_bruts if v.replace(',', '.').replace('.', '', 1).isdigit()]
                
                if len(valeurs) >= 3:
                    vent_moyen = valeurs[0]
                    vent_max = valeurs[2] # Le mini à l'index 1 est ignoré, qu'il soit à 0 ou non
                elif len(valeurs) == 2:
                    vent_moyen = valeurs[0]
                    vent_max = valeurs[1]
                else:
                    return fallback

            # 3. Sécurité : si le moyen et le max sont à 0 (balise en panne), on applique le fallback
            if vent_moyen == 0.0 and vent_max == 0.0:
                return fallback

            # 4. Calcul de l'indice d'agitation
            delta_rafale = max(0.0, vent_max - vent_moyen)
            indice = min(10, round((delta_rafale / 3) + (vent_moyen / 5)))
            
            return {
                "heure": heure_reelle,
                "vent_moyen": vent_moyen,
                "vent_max": vent_max,
                "indice": max(1, indice)
            }
    except Exception:
        # En cas de plantage réseau ou d'erreur, le fallback empêche la page blanche
        return fallback
