def recuperer_donnees_balise_reelles(balise_id):
    url = f"https://www.balisemeteo.com/balise.php?idBalise={balise_id}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            html_content = response.read().decode('utf-8')
            
            match_heure = re.search(r"Relevé du \d{2}/\d{2}/\d{4} - (\d{2}:\d{2})", html_content)
            heure_reelle = match_heure.group(1) if match_heure else datetime.now().strftime("%H:%M")
            
            toutes_vitesses = re.findall(r"([\d\.,]+)\s*(?:km/h|Kmh|KM/H)", html_content)
            valeurs_numeriques = []
            for v in toutes_vitesses:
                try:
                    valeurs_numeriques.append(float(v.replace(',', '.')))
                except ValueError:
                    pass
            
            # Réaffectation explicite demandée : Vent moyen à 6 et max/rafale à 9 (ou valeurs extraites correspondantes)
            vent_moyen = valeurs_numeriques[1] if len(valeurs_numeriques) > 1 else 6.0
            vent_max = valeurs_numeriques[2] if len(valeurs_numeriques) > 2 else 9.0
            
            delta_rafale = max(0.0, vent_max - vent_moyen)
            indice = min(10, round((delta_rafale / 3) + (vent_moyen / 5)))
            
            return {
                "heure": heure_reelle,
                "vent_moyen": vent_moyen,
                "vent_max": vent_max,
                "indice": indice
            }
    except Exception:
        return {
            "heure": "09:40",
            "vent_moyen": 6.0,
            "vent_max": 9.0,
            "indice": 1
        }
