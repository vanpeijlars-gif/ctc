import streamlit as st
import pandas as pd
import io
import requests

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="CTC Materialen Matcher – Equans",
    layout="centered"
)

# --- EQUANS THEME COLORS ---
PRIMARY = "#009FE3"
SECONDARY = "#003B5C"
BG = "#F5F7FA"

# --- CUSTOM CSS ---
st.markdown(
    f"""
    <style>
        .main {{
            background-color: {BG};
        }}
        .stButton>button {{
            background-color: {PRIMARY};
            color: white;
            border-radius: 4px;
            padding: 0.5rem 1.2rem;
            border: none;
            font-weight: 500;
        }}
        .stDownloadButton>button {{
            background-color: {SECONDARY};
            color: white;
            border-radius: 4px;
            font-weight: 500;
        }}
        .block-container {{
            padding-top: 2rem;
        }}
    </style>
    """,
    unsafe_allow_html=True
)

# --- TITLE ---
st.title("CTC Materialen Matcher")
st.write("Controleer of bestelde materialen al beschikbaar zijn binnen Equans via de CTC-marktplaats.")

st.divider()

# --- HELPER FUNCTIONS ---
def detect_column(df, possible_names):
    for col in df.columns:
        if col.lower().strip() in possible_names:
            return col
    return None

artikel_cols = {"artikelnummer", "artikel_nr", "artnr", "nummer", "sku", "code"}
naam_cols = {"omschrijving", "naam", "product", "titel", "beschrijving"}

def load_csv_from_url(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return pd.read_csv(io.StringIO(response.text), dtype=str)
    except Exception:
        return None

# --- INPUT: BESTELLIJST ---
st.header("1. Bestellijst invoeren")

col1, col2 = st.columns(2)

with col1:
    bestel_file = st.file_uploader("Upload bestellijst (CSV/Excel)", type=["csv", "xlsx"])

with col2:
    bestel_text = st.text_area("Of plak hier de bestellijst (CSV-tekst)")

if bestel_file:
    if bestel_file.name.endswith(".csv"):
        bestel_df = pd.read_csv(bestel_file, dtype=str)
    else:
        bestel_df = pd.read_excel(bestel_file, dtype=str)
elif bestel_text.strip():
    bestel_df = pd.read_csv(io.StringIO(bestel_text), dtype=str)
else:
    bestel_df = None

# --- INPUT: CTC DATA ---
st.header("2. CTC-marktplaats invoeren")

ctc_file = st.file_uploader("Upload CTC-lijst (CSV/Excel)", type=["csv", "xlsx"])
ctc_text = st.text_area("Of plak hier de CTC-lijst (CSV-tekst)")
ctc_url = st.text_input("Of vul hier een link in naar een CSV-export van de CTC-marktplaats")

if ctc_file:
    if ctc_file.name.endswith(".csv"):
        ctc_df = pd.read_csv(ctc_file, dtype=str)
    else:
        ctc_df = pd.read_excel(ctc_file, dtype=str)
elif ctc_text.strip():
    ctc_df = pd.read_csv(io.StringIO(ctc_text), dtype=str)
elif ctc_url.strip():
    ctc_df = load_csv_from_url(ctc_url)
    if ctc_df is None:
        st.error("De link kon niet worden geladen. Controleer of het een directe CSV-link is.")
else:
    ctc_df = None

st.divider()

# --- MATCHING ---
if st.button("Start matching"):

    if bestel_df is None or ctc_df is None:
        st.error("Upload of plak zowel een bestellijst als een CTC-lijst.")
        st.stop()

    # Detect columns
    bestel_num_col = detect_column(bestel_df, artikel_cols)
    bestel_name_col = detect_column(bestel_df, naam_cols)
    ctc_num_col = detect_column(ctc_df, artikel_cols)
    ctc_name_col = detect_column(ctc_df, naam_cols)

    # Start with a copy
    matched = bestel_df.copy()

    # --- MATCH OP ARTIKELNUMMER ---
    if bestel_num_col and ctc_num_col:
        bestel_df['artikelnummer_clean'] = bestel_df[bestel_num_col].str.lower().str.strip()
        ctc_df['artikelnummer_clean'] = ctc_df[ctc_num_col].str.lower().str.strip()

        matched = matched.merge(
            ctc_df,
            on="artikelnummer_clean",
            how="left",
            suffixes=("_bestel", "_ctc")
        )

        matched['match_op_nummer'] = matched['artikelnummer_clean'].notna()
    else:
        matched['match_op_nummer'] = False

    # --- MATCH OP NAAM (ALLEEN ALS VEILIG) ---
    naam_match_mogelijk = (
        bestel_name_col is not None and
        ctc_name_col is not None
    )

    if naam_match_mogelijk:
        bestel_df['naam_clean'] = bestel_df[bestel_name_col].str.lower().str.strip()
        ctc_df['naam_clean'] = ctc_df[ctc_name_col].str.lower().str.strip()

        # Alleen mergen als beide kolommen bestaan
        if 'naam_clean' in matched.columns and 'naam_clean' in ctc_df.columns:
            matched = matched.merge(
                ctc_df[['naam_clean']],
                on='naam_clean',
                how='left',
                suffixes=("", "_naam")
            )
            matched['match_op_naam'] = matched['naam_clean'].notna()
        else:
            matched['match_op_naam'] = False
    else:
        matched['match_op_naam'] = False

    # --- EINDRESULTAAT ---
    matched['match_gevonden'] = matched['match_op_nummer'] | matched['match_op_naam']

    st.success(f"Matching voltooid – {matched['match_gevonden'].sum()} matches gevonden.")
    st.dataframe(matched, use_container_width=True)

    csv = matched.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download resultaat (CSV)",
        data=csv,
        file_name="ctc_match_resultaat.csv",
        mime="text/csv"
    )
