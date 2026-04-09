import streamlit as st
import pandas as pd
import io
import requests
import re

st.title("CTC Materialen Matcher")
st.write(
    "Deze toepassing vergelijkt materialen uit een bestellijst met beschikbare items "
    "uit de CTC-marktplaats. Matching gebeurt op basis van artikelnummer en naamovereenkomst. "
    "U kunt bestanden uploaden, tekst plakken of een URL gebruiken."
)

# ---------------------------------------------------------
# Hulpfuncties
# ---------------------------------------------------------

def detect_column(df, possible_names):
    """Zoekt naar een kolomnaam die overeenkomt met bekende varianten."""
    for col in df.columns:
        if isinstance(col, str) and col.lower().strip() in possible_names:
            return col
    return None

def load_csv_from_url(url):
    """Laadt een CSV-bestand vanaf een URL."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        return pd.read_csv(io.StringIO(response.text), dtype=str)
    except Exception:
        return None

def preprocess_text_to_csv(text):
    """
    Probeert warrige tekst om te zetten naar bruikbare CSV.
    - Forceert nieuwe regels
    - Normaliseert komma's
    - Zorgt dat pandas er kolommen van kan maken
    """
    # Forceer newline tussen records: "2 , Wasco , spoed b9911" → newline voor b9911
    text = re.sub(r"(\d)\s+([A-Za-z])", r"\1\n\2", text)

    # Als er geen komma's zijn → geen CSV
    if "," not in text:
        return None

    try:
        df = pd.read_csv(io.StringIO(text), header=None, dtype=str)
        # Als er maar 1 kolom is → nog steeds niet bruikbaar
        if df.shape[1] < 2:
            return None
        return df
    except:
        return None

artikel_cols = {"artikelnummer", "artnr", "nummer", "code", "sku"}
naam_cols = {"omschrijving", "naam", "product", "titel"}

# ---------------------------------------------------------
# Bestellijst
# ---------------------------------------------------------

st.header("1. Bestellijst invoeren")

col1, col2 = st.columns(2)

with col1:
    bestel_file = st.file_uploader("Upload bestellijst (CSV/Excel)", type=["csv", "xlsx"])

with col2:
    bestel_text = st.text_area("Of plak hier de bestellijst (CSV-tekst)")

bestel_url = st.text_input("Of vul een URL in naar een CSV-bestand")

bestel_df = None

if bestel_file:
    if bestel_file.name.endswith(".csv"):
        bestel_df = pd.read_csv(bestel_file, dtype=str)
    else:
        bestel_df = pd.read_excel(bestel_file, dtype=str)

elif bestel_text.strip():
    parsed = preprocess_text_to_csv(bestel_text)
    if parsed is not None:
        bestel_df = parsed
    else:
        bestel_df = pd.read_csv(io.StringIO(bestel_text), dtype=str)

elif bestel_url.strip():
    bestel_df = load_csv_from_url(bestel_url)
    if bestel_df is None:
        st.error("De bestellijst kon niet worden geladen vanaf de URL.")

# ---------------------------------------------------------
# CTC-lijst
# ---------------------------------------------------------

st.header("2. CTC-marktplaats invoeren")

col3, col4 = st.columns(2)

with col3:
    ctc_file = st.file_uploader("Upload CTC-lijst (CSV/Excel)", type=["csv", "xlsx"])

with col4:
    ctc_text = st.text_area("Of plak hier de CTC-lijst (CSV-tekst)")

ctc_url = st.text_input("Of vul een URL in naar een CTC CSV-bestand")

ctc_df = None

if ctc_file:
    if ctc_file.name.endswith(".csv"):
        ctc_df = pd.read_csv(ctc_file, dtype=str)
    else:
        ctc_df = pd.read_excel(ctc_file, dtype=str)

elif ctc_text.strip():
    parsed = preprocess_text_to_csv(ctc_text)
    if parsed is not None:
        ctc_df = parsed
    else:
        ctc_df = pd.read_csv(io.StringIO(ctc_text), dtype=str)

elif ctc_url.strip():
    ctc_df = load_csv_from_url(ctc_url)
    if ctc_df is None:
        st.error("De CTC-lijst kon niet worden geladen vanaf de URL.")

# ---------------------------------------------------------
# Matching
# ---------------------------------------------------------

if st.button("Start matching"):

    if bestel_df is None or ctc_df is None:
        st.error("Upload, plak of laad zowel een bestellijst als een CTC-lijst.")
        st.stop()

    # Kolommen detecteren
    bestel_num = detect_column(bestel_df, artikel_cols)
    bestel_name = detect_column(bestel_df, naam_cols)
    ctc_num = detect_column(ctc_df, artikel_cols)
    ctc_name = detect_column(ctc_df, naam_cols)

    # Clean kolommen aanmaken
    bestel_df["num_clean"] = (
        bestel_df[bestel_num].str.lower().str.strip() if bestel_num else ""
    )
    bestel_df["name_clean"] = (
        bestel_df[bestel_name].str.lower().str.strip() if bestel_name else ""
    )

    ctc_df["num_clean"] = (
        ctc_df[ctc_num].str.lower().str.strip() if ctc_num else ""
    )
    ctc_df["name_clean"] = (
        ctc_df[ctc_name].str.lower().str.strip() if ctc_name else ""
    )

    # Resultaten verzamelen
    resultaten = []

    for _, row in bestel_df.iterrows():
        nummer = row["num_clean"]
        naam = row["name_clean"]

        match_op_nummer = False
        match_op_naam = False
        suggesties = []

        # Exacte match op artikelnummer
        if nummer and nummer in ctc_df["num_clean"].values:
            match_op_nummer = True
            suggesties.append("Exacte overeenkomst op artikelnummer")

        # Naamvergelijking (eenvoudige substring-check)
        if naam:
            for ctc_item in ctc_df["name_clean"].dropna():
                if naam in ctc_item or ctc_item in naam:
                    match_op_naam = True
                    suggesties.append(f"Mogelijke overeenkomst op naam: '{ctc_item}'")

        resultaten.append({
            "artikelnummer": row.get(bestel_num, ""),
            "omschrijving": row.get(bestel_name, ""),
            "match_op_nummer": match_op_nummer,
            "match_op_naam": match_op_naam,
            "suggesties": "; ".join(suggesties)
        })

    result_df = pd.DataFrame(resultaten)

    # Matches bovenaan sorteren
    result_df = result_df.sort_values(
        by=["match_op_nummer", "match_op_naam"],
        ascending=False
    )

    st.success("Matching voltooid.")
    st.dataframe(result_df, use_container_width=True)

    st.download_button(
        "Download resultaat (CSV)",
        result_df.to_csv(index=False).encode("utf-8"),
        "ctc_match_resultaat.csv",
        "text/csv"
    )
