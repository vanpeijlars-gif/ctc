import streamlit as st
import pandas as pd
import io
import zipfile
import re
from difflib import SequenceMatcher

st.markdown("# CTC Materialen Matcher")

# ---------------------------------------------------------
# PDF fallback parser (werkt zonder extra libraries)
# ---------------------------------------------------------

def extract_text_from_pdf_simple(file):
    """Zeer simpele PDF tekstextractie zonder externe libraries."""
    try:
        raw = file.read().decode("latin-1", errors="ignore")
        # PDF tekst staat vaak tussen ( ... )
        matches = re.findall(r"\((.*?)\)", raw)
        return "\n".join(matches)
    except:
        return ""

# ---------------------------------------------------------
# DOCX parser zonder libraries
# ---------------------------------------------------------

def extract_text_from_docx_simple(file):
    """Leest DOCX zonder python-docx."""
    text = ""
    with zipfile.ZipFile(file) as z:
        if "word/document.xml" in z.namelist():
            xml = z.read("word/document.xml").decode("utf-8")
            # verwijder XML tags
            cleaned = re.sub(r"<.*?>", "", xml)
            text = cleaned.replace("\n", " ")
    return text

# ---------------------------------------------------------
# Universele loader
# ---------------------------------------------------------

def load_any_table(file, text):
    df = None

    if file is not None:
        name = file.name.lower()

        # PDF
        if name.endswith(".pdf"):
            raw = extract_text_from_pdf_simple(file)
            df = pd.read_csv(
                io.StringIO(raw),
                dtype=str,
                header=None,
                sep=r"\s+",
                engine="python"
            )

        # DOCX
        elif name.endswith(".docx"):
            raw = extract_text_from_docx_simple(file)
            df = pd.read_csv(
                io.StringIO(raw),
                dtype=str,
                header=None,
                sep=r"\s+",
                engine="python"
            )

        # CSV
        elif name.endswith(".csv"):
            df = pd.read_csv(file, dtype=str, header=None)

        # Excel
        elif name.endswith(".xlsx"):
            df = pd.read_excel(file, dtype=str, header=None)

    elif text.strip():
        try:
            df = pd.read_csv(io.StringIO(text), dtype=str, header=None)
        except:
            df = pd.read_csv(
                io.StringIO(text),
                dtype=str,
                header=None,
                sep=r"\s+",
                engine="python"
            )

    if df is not None:
        df = df.fillna("")
    return df

# ---------------------------------------------------------
# Matching helpers
# ---------------------------------------------------------

def row_to_text(row):
    return " ".join(str(v) for v in row if str(v).strip() != "").lower()

def extract_numbers(text):
    return [t for t in text.split() if any(c.isdigit() for c in t)]

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

st.subheader("Bestellijst invoeren")
col1, col2 = st.columns(2)
with col1:
    bestel_file = st.file_uploader("Upload bestellijst (CSV/Excel/PDF/Word)", type=["csv","xlsx","pdf","docx"])
with col2:
    bestel_text = st.text_area("Of plak hier de bestellijst")

bestel_df = load_any_table(bestel_file, bestel_text)

st.subheader("CTC-lijst invoeren")
col3, col4 = st.columns(2)
with col3:
    ctc_file = st.file_uploader("Upload CTC-lijst (CSV/Excel/PDF/Word)", type=["csv","xlsx","pdf","docx"])
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
        b_words = extract_keywords(b_txt)
        b_type = detect_producttype(b_words)
        b_set = set(b_words)

        for j, c_txt in enumerate(ctc_texts):

            c_nums = extract_numbers(c_txt)
            c_words = extract_keywords(c_txt)
            c_type = detect_producttype(c_words)
            c_set = set(c_words)

            exact_num = len(set(b_nums) & set(c_nums)) > 0
            same_type = (b_type == c_type and b_type != "")
            overlap = len(b_set & c_set)

            if exact_num or (same_type and overlap >= 2):
                resultaten.append({
                    "Bestel regel": i,
                    "Bestel tekst": shorten(b_txt),
                    "CTC regel": j,
                    "CTC tekst": shorten(c_txt),
                    "Art.nr match": exact_num,
                    "Producttype match": same_type,
                    "Woord overlap": overlap
                })

    if not resultaten:
        st.warning("Geen overeenkomsten gevonden.")
        st.stop()

    result_df = pd.DataFrame(resultaten)

    result_df = result_df.sort_values(
        by=["Art.nr match", "Producttype match", "Woord overlap"],
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
