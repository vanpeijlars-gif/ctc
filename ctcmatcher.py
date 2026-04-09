import streamlit as st
import pandas as pd
import io
import requests
from difflib import SequenceMatcher

st.title("CTC Materialen Matcher – Hybrid Exact + Fuzzy")

# ---------------------------------------------------------
# Helper functies
# ---------------------------------------------------------

def load_any_table(file, text, url):
    """Laadt CSV/Excel/tekst/URL in als DataFrame, zonder afhankelijk te zijn van kolomnamen."""
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

    elif url.strip():
        try:
            resp = requests.get(url)
            resp.raise_for_status()
            df = pd.read_csv(io.StringIO(resp.text), dtype=str, header=None)
        except:
            df = None

    if df is not None:
        df = df.fillna("")
    return df


def row_to_text(row):
    """Combineert alle kolomwaarden tot één string."""
    return " ".join(str(v) for v in row if str(v).strip() != "").lower()


def similarity(a, b):
    """Fuzzy similarity score."""
    return SequenceMatcher(None, a, b).ratio()


def word_overlap(a, b):
    """Aantal overlappende woorden."""
    wa = set(a.split())
    wb = set(b.split())
    return len(wa & wb)


def extract_numbers(text):
    """Zoekt naar artikelnummer-achtige tokens."""
    return [t for t in text.split() if any(c.isdigit() for c in t)]


# ---------------------------------------------------------
# Invoer
# ---------------------------------------------------------

st.header("1. Bestellijst invoeren")
col1, col2 = st.columns(2)
with col1:
    bestel_file = st.file_uploader("Upload bestellijst (CSV/Excel)", type=["csv", "xlsx"])
with col2:
    bestel_text = st.text_area("Of plak hier de bestellijst")

bestel_url = st.text_input("Of URL naar bestellijst CSV")

bestel_df = load_any_table(bestel_file, bestel_text, bestel_url)

if bestel_df is not None:
    st.caption("Voorbeeld bestellijst:")
    st.dataframe(bestel_df.head())

# ---------------------------------------------------------

st.header("2. CTC-lijst invoeren")
col3, col4 = st.columns(2)
with col3:
    ctc_file = st.file_uploader("Upload CTC-lijst (CSV/Excel)", type=["csv", "xlsx"])
with col4:
    ctc_text = st.text_area("Of plak hier de CTC-lijst")

ctc_url = st.text_input("Of URL naar CTC CSV")

ctc_df = load_any_table(ctc_file, ctc_text, ctc_url)

if ctc_df is not None:
    st.caption("Voorbeeld CTC-lijst:")
    st.dataframe(ctc_df.head())

# ---------------------------------------------------------
# Matching
# ---------------------------------------------------------

st.header("3. Matching uitvoeren")

min_similarity = st.slider("Minimale fuzzy similarity", 0.0, 1.0, 0.3, 0.05)
max_suggesties = st.slider("Max suggesties per regel", 1, 10, 3)

if st.button("Start matching"):

    if bestel_df is None or ctc_df is None:
        st.error("Laad beide lijsten.")
        st.stop()

    bestel_texts = bestel_df.apply(row_to_text, axis=1)
    ctc_texts = ctc_df.apply(row_to_text, axis=1)

    resultaten = []

    for i, b_txt in enumerate(bestel_texts):

        b_nums = extract_numbers(b_txt)
        b_words = set(b_txt.split())

        matches = []

        for j, c_txt in enumerate(ctc_texts):

            c_nums = extract_numbers(c_txt)
            c_words = set(c_txt.split())

            # 1. Exact artikelnummer match
            exact_num = len(set(b_nums) & set(c_nums)) > 0

            # 2. Woord overlap
            overlap = len(b_words & c_words)

            # 3. Fuzzy similarity
            sim = similarity(b_txt, c_txt)

            # Alleen opnemen als er enige gelijkenis is
            if exact_num or overlap > 0 or sim >= min_similarity:
                matches.append((j, exact_num, overlap, sim))

        # Sorteren: exact nummer > woord overlap > fuzzy similarity
        matches.sort(key=lambda x: (x[1], x[2], x[3]), reverse=True)

        # Als geen matches → toch tonen
        if not matches:
            resultaten.append({
                "bestel_index": i,
                "bestel_tekst": b_txt,
                "ctc_index": "",
                "ctc_tekst": "",
                "exact_nummer": False,
                "woord_overlap": 0,
                "similarity": 0.0
            })
        else:
            for j, exact_num, overlap, sim in matches[:max_suggesties]:
                resultaten.append({
                    "bestel_index": i,
                    "bestel_tekst": b_txt,
                    "ctc_index": j,
                    "ctc_tekst": ctc_texts.iloc[j],
                    "exact_nummer": exact_num,
                    "woord_overlap": overlap,
                    "similarity": round(sim, 3)
                })

    result_df = pd.DataFrame(resultaten)

    # Sorteren over ALLE regels
    result_df = result_df.sort_values(
        by=["exact_nummer", "woord_overlap", "similarity"],
        ascending=False
    )

    st.success("Matching voltooid.")
    st.dataframe(result_df, use_container_width=True)

    st.download_button(
        "Download resultaat",
        result_df.to_csv(index=False).encode("utf-8"),
        "ctc_hybrid_match.csv",
        "text/csv"
    )
