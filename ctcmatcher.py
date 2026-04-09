import streamlit as st
import pandas as pd
import io
from difflib import SequenceMatcher

st.markdown("# CTC Materialen Matcher")

# ---------------------------------------------------------
# Helper functies
# ---------------------------------------------------------

def load_any_table(file, text):
    """Laadt CSV/Excel/tekst in als DataFrame, zonder afhankelijk te zijn van kolomnamen."""
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

min_similarity = st.slider("Minimale fuzzy similarity", 0.0, 1.0, 0.3, 0.05)

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

        for j, c_txt in enumerate(ctc_texts):

            c_nums = extract_numbers(c_txt)
            c_words = set(c_txt.split())

            # Exact artikelnummer match
            exact_num = len(set(b_nums) & set(c_nums)) > 0

            # Woord overlap
            overlap = len(b_words & c_words)

            # Fuzzy similarity
            sim = similarity(b_txt, c_txt)

            # Alleen opnemen als er ECHT een match is
            if exact_num or overlap > 0 or sim >= min_similarity:
                resultaten.append({
                    "Bestel regel": i,
                    "Bestel tekst": b_txt,
                    "CTC regel": j,
                    "CTC tekst": c_txt,
                    "Exact nummer match": exact_num,
                    "Woord overlap": overlap,
                    "Similarity score": round(sim, 3)
                })

    if not resultaten:
        st.warning("Geen overeenkomsten gevonden.")
        st.stop()

    result_df = pd.DataFrame(resultaten)

    # Sorteren: exact nummer > woord overlap > similarity
    result_df = result_df.sort_values(
        by=["Exact nummer match", "Woord overlap", "Similarity score"],
        ascending=False
    )

    st.success("Matching voltooid.")
    st.dataframe(result_df, use_container_width=True, height=600)

    st.download_button(
        "Download match‑resultaten",
        result_df.to_csv(index=False).encode("utf-8"),
        "ctc_matches.csv",
        "text/csv"
    )
