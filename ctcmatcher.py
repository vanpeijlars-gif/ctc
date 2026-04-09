import streamlit as st
import pandas as pd
import io

st.title("CTC Materialen Matcher")
st.write(
    "Deze toepassing vergelijkt materialen uit een bestellijst met beschikbare items "
    "uit de CTC-marktplaats. De matching is gebaseerd op artikelnummer en naamovereenkomst."
)

# ---------------------------------------------------------
# Hulpfuncties
# ---------------------------------------------------------

def detect_column(df, possible_names):
    """Zoekt naar een kolomnaam die overeenkomt met bekende varianten."""
    for col in df.columns:
        if col.lower().strip() in possible_names:
            return col
    return None

artikel_cols = {"artikelnummer", "artnr", "nummer", "code", "sku"}
naam_cols = {"omschrijving", "naam", "product", "titel"}

# ---------------------------------------------------------
# Bestellijst
# ---------------------------------------------------------

st.header("1. Bestellijst uploaden")
bestel_file = st.file_uploader("Upload een bestellijst (CSV)", type=["csv"])

if bestel_file:
    bestel_df = pd.read_csv(bestel_file, dtype=str)
else:
    bestel_df = None

# ---------------------------------------------------------
# CTC-lijst
# ---------------------------------------------------------

st.header("2. CTC-lijst uploaden")
ctc_file = st.file_uploader("Upload een CTC-lijst (CSV)", type=["csv"])

if ctc_file:
    ctc_df = pd.read_csv(ctc_file, dtype=str)
else:
    ctc_df = None

# ---------------------------------------------------------
# Matching
# ---------------------------------------------------------

if st.button("Start matching"):

    if bestel_df is None or ctc_df is None:
        st.error("Upload zowel een bestellijst als een CTC-lijst om te starten.")
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

    st.success("Matching voltooid.")
    st.dataframe(result_df, use_container_width=True)

    st.download_button(
        "Download resultaat (CSV)",
        result_df.to_csv(index=False).encode("utf-8"),
        "ctc_match_resultaat.csv",
        "text/csv"
    )
