import streamlit as st
import pandas as pd
import io

# === UI STYLING ===
st.set_page_config(
    page_title="CTC Matcher",
    page_icon="🔄",
    layout="centered"
)

PRIMARY = "#009FE3"
SECONDARY = "#003B5C"
BG = "#F5F7FA"

st.markdown(
    f"""
    <style>
        .main {{
            background-color: {BG};
        }}
        .stButton>button {{
            background-color: {PRIMARY};
            color: white;
            border-radius: 6px;
            padding: 0.6rem 1.2rem;
            border: none;
        }}
        .stDownloadButton>button {{
            background-color: {SECONDARY};
            color: white;
            border-radius: 6px;
        }}
    </style>
    """,
    unsafe_allow_html=True
)

# === TITEL ===
st.title("🔄 CTC Materialen Matcher")
st.subheader("Check automatisch of bestelde materialen al binnen Equans beschikbaar zijn")

st.write(
    "Upload een bestellijst en CTC‑lijst, of plak je bestellijst direct in het tekstvak. "
    "Het systeem matcht automatisch op **artikelnummer** en **naam** (exacte match)."
)

st.divider()

# === HELPER FUNCTIES ===
def detect_column(df, possible_names):
    for col in df.columns:
        if col.lower().strip() in possible_names:
            return col
    return None

artikel_cols = {"artikelnummer", "artikel_nr", "artnr", "nummer", "sku", "code"}
naam_cols = {"omschrijving", "naam", "product", "titel", "beschrijving"}

# === INPUT BLOK ===
st.header("1. Bestellijst invoeren")

col1, col2 = st.columns(2)

with col1:
    bestel_file = st.file_uploader("📄 Upload bestellijst (CSV/Excel)", type=["csv", "xlsx"])

with col2:
    bestel_text = st.text_area("📋 Of plak hier je bestellijst (CSV‑tekst)")

# Bestellijst verwerken
if bestel_file:
    if bestel_file.name.endswith(".csv"):
        bestel_df = pd.read_csv(bestel_file, dtype=str)
    else:
        bestel_df = pd.read_excel(bestel_file, dtype=str)
elif bestel_text.strip():
    bestel_df = pd.read_csv(io.StringIO(bestel_text), dtype=str)
else:
    bestel_df = None

st.header("2. CTC‑lijst uploaden")
ctc_file = st.file_uploader("📦 Upload CTC‑lijst (CSV/Excel)", type=["csv", "xlsx"])

if ctc_file:
    if ctc_file.name.endswith(".csv"):
        ctc_df = pd.read_csv(ctc_file, dtype=str)
    else:
        ctc_df = pd.read_excel(ctc_file, dtype=str)
else:
    ctc_df = None

st.divider()

# === MATCHING ===
if st.button("🔍 Start matching"):

    if bestel_df is None or ctc_df is None:
        st.error("❗ Upload zowel een bestellijst als een CTC‑lijst.")
        st.stop()

    # Kolommen detecteren
    bestel_num_col = detect_column(bestel_df, artikel_cols)
    bestel_name_col = detect_column(bestel_df, naam_cols)
    ctc_num_col = detect_column(ctc_df, artikel_cols)
    ctc_name_col = detect_column(ctc_df, naam_cols)

    # Exacte match op artikelnummer
    if bestel_num_col and ctc_num_col:
        bestel_df['artikelnummer_clean'] = bestel_df[bestel_num_col].str.lower().str.strip()
        ctc_df['artikelnummer_clean'] = ctc_df[ctc_num_col].str.lower().str.strip()

        matched = bestel_df.merge(
            ctc_df,
            on="artikelnummer_clean",
            how="left",
            suffixes=("_bestel", "_ctc")
        )
        matched['match_op_nummer'] = matched[ctc_name_col].notna()
    else:
        matched = bestel_df.copy()
        matched['match_op_nummer'] = False

    # Exacte match op naam
    if bestel_name_col and ctc_name_col:
        bestel_df['naam_clean'] = bestel_df[bestel_name_col].str.lower().str.strip()
        ctc_df['naam_clean'] = ctc_df[ctc_name_col].str.lower().str.strip()

        matched = matched.merge(
            ctc_df[['naam_clean']],
            left_on='naam_clean',
            right_on='naam_clean',
            how='left',
            suffixes=("", "_naam")
        )

        matched['match_op_naam'] = matched['naam_clean'].notna()
    else:
        matched['match_op_naam'] = False

    matched['match_gevonden'] = matched['match_op_nummer'] | matched['match_op_naam']

    # === RESULTAAT ===
    st.success(f"🎉 Matching voltooid — {matched['match_gevonden'].sum()} matches gevonden")

    st.dataframe(matched, use_container_width=True)

    # Download
    csv = matched.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Download resultaat (CSV)",
        data=csv,
        file_name="ctc_match_resultaat.csv",
        mime="text/csv"
    )
