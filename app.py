import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from collections import Counter
import re
import anthropic

# ─── CONFIG ───────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Babilou – Analyse satisfaction",
    page_icon="B",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── COULEURS BABILOU ─────────────────────────────────────────────────────────
BLEU       = "#02378E"
CORAIL     = "#FF7E64"
BLEU_CLAIR = "#6DBFF2"
VERT       = "#2CDB8B"
JAUNE      = "#FFCB64"
BLEU_PALE  = "#D5EEFD"

# ─── API KEY ──────────────────────────────────────────────────────────────────
API_KEY = "MACLE"

# ─── CSS BABILOU ──────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;700&family=Quicksand:wght@500;700&display=swap');
html, body, [class*="css"] {{ font-family: 'Montserrat', sans-serif; }}
h1, h2, h3 {{ font-family: 'Quicksand', sans-serif; color: {BLEU}; }}
.stMetric {{ background: {BLEU_PALE}; border-radius: 12px; padding: 12px; }}
.stMetric label {{ color: {BLEU} !important; font-size: 13px !important; }}
section[data-testid="stSidebar"] {{ background-color: {BLEU}; }}
section[data-testid="stSidebar"] p {{ color: white !important; }}
section[data-testid="stSidebar"] label {{ color: #B2C1DD !important; font-size: 12px !important; }}
section[data-testid="stSidebar"] .stRadio label {{ color: white !important; font-size: 12px !important; }}
section[data-testid="stSidebar"] .stRadio span {{ color: white !important; }}
section[data-testid="stSidebar"] .stRadio div {{ color: white !important; }}
section[data-testid="stSidebar"] .stRadio p {{ color: white !important; }}
section[data-testid="stSidebar"] .stSelectbox > div > div {{
    background-color: white !important;
    border-radius: 8px !important;
}}
section[data-testid="stSidebar"] .stSelectbox > div > div > div {{
    color: {BLEU} !important;
    font-size: 13px !important;
}}
section[data-testid="stSidebar"] .stSelectbox svg {{
    fill: {BLEU} !important;
}}
.badge-pos {{ background: #d4f5e9; color: #0a6640; padding: 3px 10px; border-radius: 8px; font-size: 12px; }}
.badge-neg {{ background: #fde8e8; color: #a32d2d; padding: 3px 10px; border-radius: 8px; font-size: 12px; }}
.badge-mix {{ background: #fff3cd; color: #854f0b; padding: 3px 10px; border-radius: 8px; font-size: 12px; }}
.badge-neu {{ background: #e9ecef; color: #495057; padding: 3px 10px; border-radius: 8px; font-size: 12px; }}
.verbatim-card {{
    background: white; border: 1px solid #e0e0e0; border-radius: 12px;
    padding: 14px 16px; margin-bottom: 10px; border-left: 4px solid {BLEU_CLAIR};
}}
.kpi-card {{
    background: white; border: 1px solid #e8edf5;
    border-radius: 12px; padding: 14px 16px; margin-bottom: 8px;
}}
.resume-box {{
    background: {BLEU_PALE}; border-left: 4px solid {BLEU};
    border-radius: 12px; padding: 16px; margin-bottom: 16px;
    font-size: 14px; color: #333; line-height: 1.7;
}}
.kpi-global-card {{
    background: white; border: 1px solid #e0e0e0; border-radius: 16px;
    padding: 20px; text-align: center; box-shadow: 0 2px 8px rgba(2,55,142,0.08);
}}
.kpi-global-label {{
    font-size: 12px; color: #888; margin-bottom: 8px; font-weight: 500;
}}
.kpi-global-value {{
    font-size: 32px; font-weight: 700; color: {BLEU};
    font-family: 'Quicksand', sans-serif;
}}
</style>
""", unsafe_allow_html=True)

# ─── MOTS CLÉS PAR ENGAGEMENT ─────────────────────────────────────────────────
MOTS_CLES = {
    "1. Securite et confiance": [
        "securite", "confiance", "rassure", "tranquille", "protege",
        "heureux", "peur", "anxieux", "sante", "incident", "accident",
        "danger", "risque", "blesse", "surveillance", "securise"
    ],
    "2. Liberte de mouvement": [
        "activite", "jeux", "jouets", "eveil", "ludique", "mouvement",
        "bouger", "motricite", "espace", "libre", "courir", "grimper",
        "corporel", "physique", "mobilite", "moteur"
    ],
    "3. Contact avec la nature": [
        "nature", "jardin", "exterieur", "plantes", "sortie", "air",
        "vert", "environnement", "dehors", "verdure", "animaux",
        "potager", "arbres", "fleurs", "promenade"
    ],
    "4. Sommeil et developpement": [
        "sommeil", "sieste", "repos", "dort", "rythme", "developpement",
        "epanouissement", "cognitif", "fatigue", "cerveau", "apprentissage",
        "progres", "grandir", "autonomie", "eveil"
    ],
    "5. Inclusion et langues": [
        "langue", "inclusion", "besoins", "diversite", "socialisation",
        "langage", "handicap", "difference", "particulier", "individuel",
        "integration", "bilinguisme", "parole", "vocabulaire", "communiquer"
    ],
    "6. Implication des familles": [
        "communication", "transmission", "information", "parents",
        "famille", "evenement", "ecoute", "implication", "parentalite",
        "application", "reunion", "partage", "quotidien", "journee",
        "lien", "relation", "dialogue", "transmissions"
    ],
}

# ─── PERCEPTION MAP ───────────────────────────────────────────────────────────
PERCEPTION_MAP = {
    "Oui, tout à fait": 10, "Oui, plutôt": 7,
    "Non, pas vraiment": 4, "Non, pas du tout": 1,
}

# ─── MAPPING ENGAGEMENTS ──────────────────────────────────────────────────────
ENGAGEMENTS = {
    "1. Securite et confiance": {
        "color": BLEU,
        "kpis": [
            "La relation de confiance",
            "La sécurité affective",
            "La sécurité au sein de l'établissement",
            "Q29_NIveau de confiance",
            "Management of incident",
            "L'attention portée à la santé de l'enfant",
        ]
    },
    "2. Liberte de mouvement": {
        "color": VERT,
        "kpis": [
            "Les jeux libres, l'éveil et l'accès aux jouets",
            "Les propositions d'éveil et d'activités ludiques",
        ]
    },
    "3. Contact avec la nature": {"color": "#79E673", "kpis": []},
    "4. Sommeil et developpement": {
        "color": BLEU_CLAIR,
        "kpis": [
            "La qualité du sommeil",
            "Q14-Respect du rythme de l'enfant",
            "Son développement et son épanouissement",
        ]
    },
    "5. Inclusion et langues": {
        "color": JAUNE,
        "kpis": [
            "La prise en compte des besoins particuliers de l'enfant",
            "L'acquisition du langage",
            "Sa socialisation",
        ]
    },
    "6. Implication des familles": {
        "color": CORAIL,
        "kpis": [
            "La qualité des transmissions",
            "Q27 Qualité des transmissions",
            "L'information aux familles",
            "Les actions de soutien à la parentalité",
            "Les évènements familles",
            "Q31_Outils de Communication",
            "Perception écoute parents",
            "Perception implication parents",
        ]
    },
}

# ─── VERBATIMS ET SENTIMENTS ──────────────────────────────────────────────────
VERBATIM_COLS = {
    "Experience creche":         "Q49 Expérience crèche",
    "Raisons de recommandation": "Q43 Raisons reco",
    "Suggestions familles":      "Q12 Suggestions relation famille",
}

SENTIMENT_COLS = {
    "Experience creche":         "sentiment_experience",
    "Raisons de recommandation": "sentiment_reco",
    "Suggestions familles":      "sentiment_suggestions",
}

SENTIMENT_ORDER = ["Very Positive", "Positive", "Mixed", "Neutral", "Negative", "Very Negative"]
SENTIMENT_LABEL = {
    "Very Positive": "Tres positif", "Positive": "Positif",
    "Mixed": "Mixte", "Neutral": "Neutre",
    "Negative": "Negatif", "Very Negative": "Tres negatif",
}
SENTIMENT_BADGE = {
    "Very Positive": "badge-pos", "Positive": "badge-pos",
    "Mixed": "badge-mix", "Neutral": "badge-neu",
    "Negative": "badge-neg", "Very Negative": "badge-neg",
}

# ─── LOAD DATA ────────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    df = pd.read_excel("SATVerbatim.xlsx")
    for col in ["Perception écoute parents", "Perception implication parents"]:
        if col in df.columns:
            df[col + "_num"] = df[col].map(PERCEPTION_MAP)
    return df

df_raw = load_data()

# ─── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    try:
        st.image("logo_babilou.jpg", use_container_width=True)
    except:
        st.markdown(f"<div style='text-align:center;padding:10px 0;'><span style='font-size:22px;font-weight:700;color:white;'>Babilou</span></div>", unsafe_allow_html=True)

    st.markdown("<p style='font-size:11px;color:#B2C1DD;text-align:center;margin-bottom:16px;'>Analyse satisfaction parents</p>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("<p style='font-size:10px;color:#B2C1DD;letter-spacing:0.1em;'>FILTRES</p>", unsafe_allow_html=True)

    verbatim_type = st.selectbox("Type de verbatim", list(VERBATIM_COLS.keys()))
    SENTIMENT_COL = SENTIMENT_COLS.get(verbatim_type, "sentiment_experience")
    sent_vals = df_raw[SENTIMENT_COL].dropna().unique().tolist() if SENTIMENT_COL in df_raw.columns else []
    sent_options = ["Tous"] + [SENTIMENT_LABEL.get(s, s) for s in SENTIMENT_ORDER if s in sent_vals]
    sent_filter_label = st.selectbox("Sentiment", sent_options)

    dr_options = ["Tous"] + sorted(df_raw["DR"].dropna().unique().tolist()) if "DR" in df_raw.columns else ["Tous"]
    dr_filter = st.selectbox("DR", dr_options)

    st.markdown("---")
    st.markdown("<p style='font-size:10px;color:#B2C1DD;letter-spacing:0.1em;'>NAVIGATION</p>", unsafe_allow_html=True)
    page = st.radio("", ["Vue globale"] + list(ENGAGEMENTS.keys()), label_visibility="collapsed")

# ─── FILTER DATA ──────────────────────────────────────────────────────────────
df_f = df_raw.copy()
if dr_filter != "Tous" and "DR" in df_f.columns:
    df_f = df_f[df_f["DR"] == dr_filter]

label_to_key = {v: k for k, v in SENTIMENT_LABEL.items()}
sent_filter = label_to_key.get(sent_filter_label, "Tous") if sent_filter_label != "Tous" else "Tous"
vcol = VERBATIM_COLS.get(verbatim_type, "Q49 Expérience crèche")
SENTIMENT_COL = SENTIMENT_COLS.get(verbatim_type, "sentiment_experience")

# ─── HELPER FUNCTIONS ─────────────────────────────────────────────────────────
def score_engagement(df, kpis):
    scores = []
    for kpi in kpis:
        col = kpi + "_num" if kpi in ["Perception écoute parents", "Perception implication parents"] else kpi
        if col in df.columns:
            vals = pd.to_numeric(df[col], errors='coerce').dropna()
            if len(vals) > 0 and vals.max() <= 10:
                scores.append(vals.mean())
    return round(sum(scores) / len(scores), 1) if scores else None

def score_color(score):
    if score is None: return "#aaa"
    if score >= 8.5: return VERT
    if score >= 7: return JAUNE
    return CORAIL

def sentiment_counts(df):
    if SENTIMENT_COL not in df.columns: return {}
    return df[SENTIMENT_COL].value_counts().to_dict()

def top_words(df, col, n=15):
    texts = df[col].dropna().astype(str).str.lower()
    stopwords = {
        "le","la","les","un","une","des","du","de","d","l",
        "a","au","aux","en","dans","sur","sous","par","pour",
        "avec","sans","chez","vers","entre","pendant","depuis",
        "et","ou","mais","donc","or","ni","car","que","qu",
        "je","j","tu","il","elle","on","nous","vous","ils","elles",
        "me","m","te","t","se","s","lui","leur","leurs",
        "mon","ma","mes","ton","ta","tes","son","sa","ses",
        "notre","nos","votre","vos","ce","cet","cette","ces","cela","ca",
        "est","sont","etre","être","ete","été","avoir","ont",
        "fait","faire","peut","peuvent","doit","doivent",
        "tres","très","plus","moins","bien","mal","toujours",
        "jamais","souvent","parfois","encore","aussi","ainsi",
        "tout","toute","tous","toutes","chaque","plusieurs",
        "quelques","beaucoup","peu","assez",
        "nan","ras","rien","aucun","aucune","ok","oui","non",
        "enfant","enfants","fils","fille",
        "creche","crèche","babilou",
        "parents","parent","personnel",
        "equipe","équipe","professionnels","professionnel",
        "merci","bravo","super","suis","sommes","etes","êtes",
        "notamment","egalement","également","afin","lorsque","quand"
    }
    words = []
    for text in texts:
        words.extend([w for w in re.findall(r'\b[a-z]{4,}\b', text) if w not in stopwords])
    return Counter(words).most_common(n)

def filter_by_engagement(df, col, engagement):
    if engagement not in MOTS_CLES or col not in df.columns:
        return df
    pattern = "|".join(MOTS_CLES[engagement])
    mask = df[col].fillna("").str.lower().str.contains(pattern, na=False)
    return df[mask]

def get_sub_df(df, col, engagement, sent_filter):
    sub = filter_by_engagement(df, col, engagement) if engagement else df.copy()
    if sent_filter != "Tous" and SENTIMENT_COL in sub.columns:
        sub = sub[sub[SENTIMENT_COL] == sent_filter]
    return sub.dropna(subset=[col])

def resumer_ia(verbatims, engagement, sent_label):
    try:
        client = anthropic.Anthropic(api_key=API_KEY)
        sample = verbatims[:80]
        texte = "\n---\n".join(sample)
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1200,
            messages=[{
                "role": "user",
                "content": f"""Tu es un expert Voix du Client et satisfaction parents pour Babilou, specialiste de la petite enfance.

Tu dois analyser uniquement les verbatims fournis ci-dessous.
Engagement analyse : "{engagement}"
Filtre de sentiment selectionne : "{sent_label}"
Nombre de verbatims fournis : {len(sample)}

Objectif :
Produire une synthese claire, utile pour un responsable Babilou, afin d'identifier les forces, irritants et actions prioritaires.

Consignes importantes :
- Base-toi uniquement sur les verbatims fournis.
- N'invente aucune information absente des verbatims.
- Ne generalise pas a toute l'enquete si les verbatims sont peu nombreux.
- Regroupe les idees similaires.
- Priorise les themes recurrents plutot que les cas isoles.
- Si un point est cite par peu de parents, indique qu'il s'agit d'un signal ponctuel.
- Ne repete pas simplement les verbatims.
- Utilise un ton professionnel, clair et synthetique.
- Evite les phrases vagues comme "les parents sont globalement satisfaits" sans expliquer pourquoi.

Structure obligatoire :

1. TENDANCE GENERALE
En 2 a 3 phrases, resume le ressenti dominant sur cet engagement.

2. POINTS FORTS
Liste 2 a 4 points forts reellement presents dans les verbatims.
Pour chaque point, explique brievement ce que les parents valorisent.

3. POINTS D'AMELIORATION
Liste 2 a 4 irritants, attentes ou manques identifies.
Pour chaque point, explique brievement le probleme exprime.

4. RECOMMANDATION PRIORITAIRE
Propose une seule action concrete, realiste et prioritaire pour Babilou.
La recommandation doit etre directement reliee aux verbatims.

5. NIVEAU DE CONFIANCE DE LA SYNTHESE
Indique :
- Eleve si les verbatims sont nombreux et coherents
- Moyen si plusieurs themes apparaissent mais restent disperses
- Faible si les verbatims sont peu nombreux ou contradictoires

Verbatims :
{texte}"""
            }]
        )
        return response.content[0].text
    except Exception as e:
        return f"Resume indisponible : {e}"

def display_verbatims(sub):
    if len(sub) == 0:
        st.info("Aucun verbatim trouve pour ces filtres.")
        return
    if page in MOTS_CLES and vcol in sub.columns:
        mots = MOTS_CLES[page]
        sub = sub.copy()
        sub["_score"] = sub[vcol].fillna("").str.lower().apply(
            lambda x: sum(1 for m in mots if m in x)
        )
        sub = sub.sort_values("_score", ascending=False)
    st.markdown(f"**{len(sub)} verbatims**")
    for _, row in sub.head(50).iterrows():
        sent = row[SENTIMENT_COL] if SENTIMENT_COL in row.index and pd.notna(row.get(SENTIMENT_COL)) else ""
        badge_class = SENTIMENT_BADGE.get(sent, "badge-neu")
        label = SENTIMENT_LABEL.get(sent, sent)
        st.markdown(f"""
        <div class='verbatim-card'>
            <span class='{badge_class}'>{label}</span>
            <p style='margin-top:8px;font-size:14px;color:#333;line-height:1.6;'>{str(row[vcol])}</p>
        </div>
        """, unsafe_allow_html=True)

# ─── PAGE VUE GLOBALE ─────────────────────────────────────────────────────────
if page == "Accueil":
    st.markdown("<h1>Tableau de bord satisfaction</h1>", unsafe_allow_html=True)

    # ── SECTION 1 — KPI GLOBAUX ──────────────────────────────────────────────
    st.markdown("<h2>Indicateurs cles</h2>", unsafe_allow_html=True)

    sat_globale = pd.to_numeric(df_f["Q4_1 SAT globale"], errors='coerce').mean()
    nps = pd.to_numeric(df_f["Q42_NPS score"], errors='coerce').mean()
    confiance = pd.to_numeric(df_f["Q29_NIveau de confiance"], errors='coerce').mean() if "Q29_NIveau de confiance" in df_f.columns else None

    c1, c2, c3, c4 = st.columns(4)
    for col, label, val, suffix in [
        (c1, "Satisfaction globale", sat_globale, "/10"),
        (c2, "Niveau de confiance", confiance, "/10"),
        (c3, "NPS moyen", nps, ""),
        (c4, "Taux de recommandation", 95, "%"),
    ]:
        if label == "Taux de recommandation":
            val_str = "95%"
        else:
            val_str = f"{val:.1f}{suffix}" if val is not None and not pd.isna(val) else "—"
        col.markdown(f"""
        <div class='kpi-global-card'>
            <div class='kpi-global-label'>{label}</div>
            <div class='kpi-global-value'>{val_str}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── SECTION 2 — COMPARAISON DES ENGAGEMENTS ───────────────────────────────
    st.markdown("<h2>Comparaison des engagements</h2>", unsafe_allow_html=True)

    scores = {eng: score_engagement(df_f, meta["kpis"]) if meta["kpis"] else None for eng, meta in ENGAGEMENTS.items()}

    eng_labels = [eng.split(". ")[1] for eng in ENGAGEMENTS]
    eng_scores = [scores[eng] if scores[eng] is not None else 0 for eng in ENGAGEMENTS]
    eng_colors = [score_color(scores[eng]) for eng in ENGAGEMENTS]

    fig_eng = go.Figure(go.Bar(
        x=eng_scores,
        y=eng_labels,
        orientation='h',
        marker_color=eng_colors,
        text=[f"{s}/10" if s > 0 else "Non mesure" for s in eng_scores],
        textposition='outside',
    ))
    fig_eng.update_layout(
        height=320,
        xaxis=dict(range=[0, 10], title="Score moyen"),
        yaxis=dict(title=""),
        margin=dict(l=0, r=80, t=20, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
    )
    st.plotly_chart(fig_eng, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── SECTION 3 — RÉPARTITION DES VERBATIMS PAR ENGAGEMENT ─────────────────
    st.markdown("<h2>Repartition des verbatims par engagement</h2>", unsafe_allow_html=True)

    verbatim_data = []
    for eng, mots in MOTS_CLES.items():
        eng_label = eng.split(". ")[1]
        pattern = "|".join(mots)
        for vtype, vcol_name in VERBATIM_COLS.items():
            if vcol_name in df_f.columns:
                count = df_f[vcol_name].fillna("").astype(str).str.lower().str.contains(pattern, na=False).sum()
                verbatim_data.append({"Engagement": eng_label, "Type": vtype, "Nombre": count})

    df_vb = pd.DataFrame(verbatim_data)
    fig_vb = px.bar(
        df_vb, x="Nombre", y="Engagement", color="Type",
        orientation='h', barmode='group',
        color_discrete_map={
            "Experience creche": BLEU,
            "Raisons de recommandation": BLEU_CLAIR,
            "Suggestions familles": CORAIL,
        },
        text="Nombre"
    )
    fig_vb.update_layout(
        height=380,
        xaxis=dict(title="Nombre de verbatims"),
        yaxis=dict(title=""),
        margin=dict(l=0, r=60, t=20, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig_vb.update_traces(textposition='outside')
    st.plotly_chart(fig_vb, use_container_width=True)

# ─── PAGE ENGAGEMENT ──────────────────────────────────────────────────────────
elif page in ENGAGEMENTS:
    meta = ENGAGEMENTS[page]
    score = score_engagement(df_f, meta["kpis"])

    st.markdown(f"<h1>{page}</h1>", unsafe_allow_html=True)

    if not meta["kpis"]:
        st.info("Cet engagement n'est pas mesure directement dans l'enquete. Analyse basee sur les verbatims et mots cles.")

    # ── BLOC 1 — KPI ENGAGEMENT ───────────────────────────────────────────────
    st.markdown("<h2>Indicateurs</h2>", unsafe_allow_html=True)

    sub_kpi = get_sub_df(df_f, vcol, page, "Tous")
    sent_eng = sentiment_counts(sub_kpi)
    total_eng = sum(sent_eng.values())
    pos_pct = round((sent_eng.get("Very Positive",0)+sent_eng.get("Positive",0))/total_eng*100) if total_eng else 0
    neg_pct = round((sent_eng.get("Very Negative",0)+sent_eng.get("Negative",0))/total_eng*100) if total_eng else 0
    mix_pct = round(sent_eng.get("Mixed",0)/total_eng*100) if total_eng else 0

    c1, c2, c3, c4 = st.columns(4)
    for col, label, val in [
        (c1, "Score engagement", f"{score}/10" if score else "—"),
        (c2, "Positifs", f"{pos_pct}%"),
        (c3, "Negatifs", f"{neg_pct}%"),
        (c4, "Mixtes", f"{mix_pct}%"),
    ]:
        col.markdown(f"""
        <div class='kpi-global-card'>
            <div class='kpi-global-label'>{label}</div>
            <div class='kpi-global-value'>{val}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── BLOC 2 — GRAPHIQUE DES QUESTIONS ──────────────────────────────────────
    if meta["kpis"]:
        st.markdown("<h2>Detail des questions</h2>", unsafe_allow_html=True)

        kpi_scores = []
        for kpi in meta["kpis"]:
            col = kpi + "_num" if kpi in ["Perception écoute parents", "Perception implication parents"] else kpi
            if col in df_f.columns:
                vals = pd.to_numeric(df_f[col], errors='coerce').dropna()
                if len(vals) > 0 and vals.max() <= 10:
                    kpi_scores.append((kpi, round(vals.mean(), 1), len(vals)))

        if kpi_scores:
            kpi_scores.sort(key=lambda x: x[1])
            fig = go.Figure(go.Bar(
                x=[s for _, s, _ in kpi_scores],
                y=[k[:45]+"..." if len(k) > 45 else k for k, _, _ in kpi_scores],
                orientation='h',
                marker_color=[score_color(s) for _, s, _ in kpi_scores],
                text=[f"{s}/10" for _, s, _ in kpi_scores],
                textposition='outside',
                customdata=[[n] for _, _, n in kpi_scores],
                hovertemplate='%{y}<br>Score : %{x}/10<br>Reponses : %{customdata[0]:,}<extra></extra>'
            ))
            fig.update_layout(
                height=max(250, len(kpi_scores) * 55),
                xaxis=dict(range=[0, 10], title="Note moyenne"),
                yaxis=dict(title=""),
                margin=dict(l=0, r=80, t=20, b=0),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── BLOC 3 — RÉSUMÉ IA ────────────────────────────────────────────────────
    st.markdown("<h2>Resume IA</h2>", unsafe_allow_html=True)

    sub_df = get_sub_df(df_f, vcol, page, sent_filter)

    if len(sub_df) > 0:
        if st.button(f"Generer le resume ({sent_filter_label})", key=f"resume_{page}"):
            with st.spinner("Generation en cours..."):
                resume = resumer_ia(
                    sub_df[vcol].dropna().astype(str).tolist(),
                    page, sent_filter_label
                )
                st.markdown(f"<div class='resume-box'>{resume}</div>", unsafe_allow_html=True)
    else:
        st.info("Aucun verbatim disponible pour ces filtres.")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── BLOC 4 — VERBATIMS ────────────────────────────────────────────────────
    st.markdown("<h2>Verbatims parents</h2>", unsafe_allow_html=True)

    if len(sub_df) > 0 and vcol in sub_df.columns:
        words = top_words(sub_df, vcol)
        if words:
            st.markdown("<h3>Mots cles frequents</h3>", unsafe_allow_html=True)
            word_html = " ".join([
                f"<span style='background:{BLEU_PALE};color:{BLEU};padding:4px 10px;border-radius:20px;font-size:13px;margin:3px;display:inline-block;'>{w} <b>({c})</b></span>"
                for w, c in words
            ])
            st.markdown(f"<div style='line-height:2.2;'>{word_html}</div>", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

    display_verbatims(sub_df)