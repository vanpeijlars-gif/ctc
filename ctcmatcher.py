import streamlit as st
import pandas as pd
import io
import re

st.markdown("# CTC Materialen Matcher (tekst-invoer)")

# ---------------------------------------------------------
# Helper: tekst → DataFrame
# ---------------------------------------------------------

def load_text_table(text):
    if not text.strip():
        return None

    try:
        # Probeer CSV-structuur
        df = pd.read_csv(io.StringIO(text), dtype=str, header=None)
    except:
        # Val terug op whitespace-scheiding
        df = pd.read_csv(io.StringIO(text), dtype=str, header=None, sep=r"\s+", engine="python")

    return df.fillna("")

# ---------------------------------------------------------
# Matching helpers
# ---------------------------------------------------------

def row_to_text(row):
    return " ".join(str(v) for v in row if str(v).strip() != "").lower()

def extract_artikelnummer(text):
    """Exact artikelnummer detectie: letters + cijfers."""
    for p in text.split():
        if re.match(r"^[a-zA-Z]+\d+$", p):
            return p.lower()
    return None

def extract_keywords(text):
    blacklist = {
        "prijs","onbekend","technische","unie","wasco","project","leverancier",
        "besteld","extra","info","notitie","qty","aantal","stuk","stuks",
        "mm","cm","meter","volt","230v","4000k","kelvin"
    }
    words = [w for w in text.split() if w not in blacklist and len(w) > 2]
    return words

def detect_producttype(words):
    return words[0] if words else ""

def shorten(text, length=40):
    return text[:length] + ("..." if len(text) > length else "")

# ---------------------------------------------------------
# UI invoer
# ---------------------------------------------------------

st.subheader("Bestellijst (plak hier de tekst)")
bestel_text = st.text_area("Plak bestellijst hier", height=200)

st.subheader("CTC-lijst (plak hier de tekst)")
ctc_text = st.text_area("Plak CTC-lijst hier", height=200)

# ---------------------------------------------------------
# MATCH KNOP
# ---------------------------------------------------------

if st.button("Start matching"):

    bestel_df = load_text_table(bestel_text)
    ctc_df = load_text_table(ctc_text)

    if bestel_df is None or ctc_df is None:
        st.error("Beide lijsten moeten tekst bevatten.")
        st.stop()

    bestel_texts = bestel_df.apply(row_to_text, axis=1)
    ctc_texts = ctc_df.apply(row_to_text, axis=1)

    resultaten = []

    for i, b_txt in enumerate(bestel_texts):

        b_art = extract_artikelnummer(b_txt)
        b_words = extract_keywords(b_txt)
        b_type = detect_producttype(b_words)
        b_set = set(b_words)

        for j, c_txt in enumerate(ctc_texts):

            c_art = extract_artikelnummer(c_txt)
            c_words = extract_keywords(c_txt)
            c_type = detect_producttype(c_words)
            c_set = set(c_words)

            # EXACT artikelnummer match
            exact_num = (b_art is not None and b_art == c_art)

            # Producttype exact gelijk
            same_type = (b_type == c_type and b_type != "")

            # Minimaal 2 kernwoorden overlap
            overlap = len(b_set & c_set)

            # Superstrenge match:
            if exact_num or (same_type and overlap >= 2):
                resultaten.append({
                    "Bestel regel": i,
                    "Bestel tekst": shorten(b_txt),
                    "CTC regel": j,
                    "CTC tekst": shorten(c_txt),
                    "Exact art.nr": exact_num,
                    "Producttype match": same_type,
                    "Woord overlap": overlap
                })

    if not resultaten:
        st.warning("Geen overeenkomsten gevonden.")
        st.stop()

    result_df = pd.DataFrame(resultaten)

    result_df = result_df.sort_values(
        by=["Exact art.nr", "Producttype match", "Woord overlap"],
        ascending=False
    )

    st.success("Matching voltooid.")
    st.dataframe(result_df, use_container_width=True, height=500)

    st.download_button(
        "Download match-resultaten",
        result_df.to_csv(index=False).encode("utf-8"),
        "ctc_matches.csv",
        "text/csv"
    )
