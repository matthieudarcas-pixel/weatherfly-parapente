import streamlit as st
import pandas as pd

# Configuration de la page
st.set_page_config(
    page_title="Guide & Météo des Spots de Parapente",
    page_icon="🪂",
    layout="wide"
)

# 1. Chargement des données (Lit ton fichier spots.txt avec le séparateur ';')
@st.cache_data
def load_data():
    try:
        # Note : Si ton fichier est sur GitHub, tu peux remplacer "spots.txt" par son URL Raw
        return pd.read_csv("spots.txt", sep=";")
    except FileNotFoundError:
        # Données de secours si le fichier spots.txt est manquant au premier lancement
        data = {
            "Région": ["Auvergne-Rhône-Alpes", "Auvergne-Rhône-Alpes", "Occitanie", "Bretagne"],
            "Département": ["74 - Haute-Savoie", "38 - Isère", "65 - Hautes-Pyrénées", "29 - Finistère"],
            "Nom du Site": ["Montmin (Col de la Forclaz) - Spot #1", "Saint-Hilaire du Touvet - Spot #1", "Val Louron - Spot #1", "Menez-Hom - Spot #1"],
            "Orientations Déco": ["N, NE, O", "SE, E", "N, NE", "O, SO, NO"],
            "Interdit par vent de Sud": ["Non", "Non", "Non", "Non"],
            "Conseils & Spécificités du Spot": [
                "Site thermique de montagne majeur. Attention aux confluences en altitude et au renforcement des brises de vallée l'après-midi.",
                "Site thermique de montagne majeur. Attention aux confluences en altitude et au renforcement des brises de vallée l'après-midi.",
                "Attention au vent météo de Sud (effet de Foehn marqué). Les cycles thermiques peuvent être puissants au printemps.",
                "Soaring dynamique côtier. Gestion fine de la marée basse obligatoire pour le posé de secours sur la plage."
            ],
            "Lien BaliseMétéo Direct": [
                "https://www.balisemeteo.com/balise.php?idBalise=101",
                "https://www.balisemeteo.com/balise.php?idBalise=185",
                "https://www.balisemeteo.com/balise.php?idBalise=520",
                "https://www.balisemeteo.com/balise.php?idBalise=840"
            ]
        }
        return pd.DataFrame(data)

df = load_data()

# Titre principal de la page
st.title("🪂 Guide des Spots de Parapente & Balises Météo")
st.markdown("Recherchez un spot, consultez les spécificités aérologiques locales et accédez directement aux balises météo.")

# 2. Barre latérale de filtres avancés
st.sidebar.header("🔍 Filtres de Recherche")

# Filtre Région
list_regions = sorted(df["Région"].unique())
selected_region = st.sidebar.selectbox("Sélectionner une Région", ["Toutes"] + list_regions)

# Filtre Département (se met à jour de façon dynamique selon la région choisie)
if selected_region != "Toutes":
    df_filtered = df[df["Région"] == selected_region]
else:
    df_filtered = df

list_deps = sorted(df_filtered["Département"].unique())
selected_dep = st.sidebar.selectbox("Sélectionner un Département", ["Tous"] + list_deps)

if selected_dep != "Tous":
    df_filtered = df_filtered[df_filtered["Département"] == selected_dep]

# Filtre par Orientation de Décollage (N, S, SE, etc.)
all_orientations = set()
for orientations in df["Orientations Déco"].dropna():
    for o in orientations.split(","):
        all_orientations.add(o.strip())
selected_orientation = st.sidebar.selectbox("Filtrer par Orientation Déco", ["Toutes"] + sorted(list(all_orientations)))

if selected_orientation != "Toutes":
    df_filtered = df_filtered[df_filtered["Orientations Déco"].str.contains(selected_orientation, na=False)]


# 3. Affichage des résultats dynamiques
st.subheader(f"📍 {len(df_filtered)} spot(s) trouvé(s)")

if not df_filtered.empty:
    for index, row in df_filtered.iterrows():
        # Utilisation de blocs dépliants (Expander) pour une interface propre et aérée
        with st.expander(f"🔹 {row['Nom du Site']} ({row['Département']})"):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"**🧭 Orientations Déco :** `{row['Orientations Déco']}`")
                st.markdown(f"**⚠️ Interdit par vent de Sud :** `{row['Interdit par vent de Sud']}`")
                
                # Mise en valeur de la colonne Spécificités / Conseils
                st.info(f"💡 **Particularités et conseils du spot :**\n\n{row['Conseils & Spécificités du Spot']}")
            
            with col2:
                st.markdown("<br>", unsafe_allow_html=True) # Espacement vertical pour centrer le bouton
                # Bouton moderne pour ouvrir la balise météo officielle
                st.link_button("🌐 Voir la Balise Météo", row["Lien BaliseMétéo Direct"], use_container_width=True)
else:
    st.warning("Aucun spot ne correspond à vos critères de recherche.")


# 4. Optionnel : Affichage sous forme de tableau complet
st.markdown("---")
if st.checkbox("Afficher la base de données brute sous forme de tableau"):
    st.dataframe(df_filtered, use_container_width=True)
