import streamlit as st
import pandas as pd
import io
from difflib import SequenceMatcher

st.markdown("# CTC Materialen Matcher")

# ---------------------------------------------------------
# Helper functies
# ---------------------------------------------------------

def load_any_table(file, text):
    df = None
    if file is not None:
        if file.name.endswith(".csv"):
            df = pd.read_csv(file, dtype=str, header=None)
        else:
            df = pd.read_excel(file, dtype=str, header=None)
    elif text.strip():
        try:
            df = pd.read_csv(io.StringIO(text), dtype=str, header=None)
        except:
            df = pd.read_csv(io.StringIO(text), dtype=str, header=None, sep=r"\s+")
    if df is not None:
        df = df.fillna("")
    return df


def row_to_text(row):
    return " ".join(str(v) for v in row if str(v).strip() != "").lower()


def similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()


def extract_numbers(text):
    return [t for t in text.split() if any(c.isdigit() for c in t)]


def extract_keywords(text):
    """Filtert alleen echte productwoorden, geen rommel."""
    blacklist = {
        "prijs", "onbekend", "technische", "unie", "wasco", "project", "leverancier",
        "besteld", "extra", "info", "notitie", "qty", "aantal", "stuk", "stuks"
    }
    words = [w for w in text.split() if w not in blacklist and len(w) > 2]
    return set(words)


def shorten(text, length=40):
    return text[:length] + ("..." if len(text) > length else "")


# ---------------------------------------------------------
# Invoer Bestellijst
# ---------------------------------------------------------

st.subheader("Bestellijst invoeren")

col1, col2 = st.columns(2)
with col1:
    bestel_file = st.file_uploader("Upload bestellijst (CSV/Excel)", type=["csv", "xlsx"])
with col2:
    bestel_text = st.text_area("Of plak hier de bestellijst")

bestel_df = load_any_table(bestel_file, bestel_text)

# ---------------------------------------------------------
# Invoer CTC-lijst
# ---------------------------------------------------------

st.subheader("CTC-lijst invoeren")

col3, col4 = st.columns(2)
with col3:
    ctc_file = st.file_uploader("Upload CTC-lijst (CSV/Excel)", type=["csv", "xlsx"])
with col4:
    ctc_text = st.text_area("Of plak hier de CTC-lijst")

ctc_df = load_any_table(ctc_file, ctc_text)

# ---------------------------------------------------------
# MATCH KNOP
# ---------------------------------------------------------

st.subheader("Matching uitvoeren")

if st.button("Start matching"):

    if bestel_df is None or ctc_df is None:
        st.error("Laad beide lijsten.")
        st.stop()

    bestel_texts = bestel_df.apply(row_to_text, axis=1)
    ctc_texts = ctc_df.apply(row_to_text, axis=1)

    resultaten = []

    for i, b_txt in enumerate(bestel_texts):

        b_nums = extract_numbers(b_txt)
        b_keywords = extract_keywords(b_txt)

        for j, c_txt in enumerate(ctc_texts):

            c_nums = extract_numbers(c_txt)
            c_keywords = extract_keywords(c_txt)

            # 1. Exact artikelnummer match
            exact_num = len(set(b_nums) & set(c_nums)) > 0

            # 2. Strenge productwoord-overlap
            overlap = len(b_keywords & c_keywords)

            # 3. Similarity alleen voor ranking
            sim = similarity(b_txt, c_txt)

            # SUPERSTRENG:
            # Alleen tonen als:
            # - artikelnummer matcht
            # - OF minimaal 3 echte productwoorden overeenkomen
            if exact_num or overlap >= 3:
                resultaten.append({
                    "Bestel regel": i,
                    "Bestel tekst": shorten(b_txt),
                    "CTC regel": j,
                    "CTC tekst": shorten(c_txt),
                    "Art.nr match": exact_num,
                    "Productwoord overlap": overlap,
                    "Similarity": round(sim, 3)
                })

    if not resultaten:
        st.warning("Geen overeenkomsten gevonden.")
        st.stop()

    result_df = pd.DataFrame(resultaten)

    # Ranking: artikelnummer > productwoorden > similarity
    result_df = result_df.sort_values(
        by=["Art.nr match", "Productwoord overlap", "Similarity"],
        ascending=False
    )

    st.success("Matching voltooid.")
    st.dataframe(result_df, use_container_width=True, height=500)

    st.download_button(
        "Download match‑resultaten",
        result_df.to_csv(index=False).encode("utf-8"),
        "ctc_matches.csv",
        "text/csv"
    )
