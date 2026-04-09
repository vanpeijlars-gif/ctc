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

    # Voeg lege kolommen toe zodat er nooit KeyErrors komen
    matched["match_op_nummer"] = False
    matched["match_op_naam"] = False
    matched["suggestie"] = ""

    # Clean kolommen aanmaken als ze bestaan
    if bestel_num_col:
        matched["artikelnummer_clean"] = matched[bestel_num_col].str.lower().str.strip()
    else:
        matched["artikelnummer_clean"] = ""

    if bestel_name_col:
        matched["naam_clean"] = matched[bestel_name_col].str.lower().str.strip()
    else:
        matched["naam_clean"] = ""

    if ctc_num_col:
        ctc_df["artikelnummer_clean"] = ctc_df[ctc_num_col].str.lower().str.strip()
    else:
        ctc_df["artikelnummer_clean"] = ""

    if ctc_name_col:
        ctc_df["naam_clean"] = ctc_df[ctc_name_col].str.lower().str.strip()
    else:
        ctc_df["naam_clean"] = ""

    # --- MATCH OP ARTIKELNUMMER ---
    if bestel_num_col and ctc_num_col:
        for i, row in matched.iterrows():
            num = row["artikelnummer_clean"]
            if num in ctc_df["artikelnummer_clean"].values:
                matched.at[i, "match_op_nummer"] = True
                matched.at[i, "suggestie"] = "Exacte match op artikelnummer"

    # --- MATCH OP NAAM (simpele fuzzy check) ---
    if bestel_name_col and ctc_name_col:
        for i, row in matched.iterrows():
            naam = row["naam_clean"]

            # simpele fuzzy: check of woorden overlappen
            for ctc_naam in ctc_df["naam_clean"].dropna():
                if naam != "" and ctc_naam != "":
                    if naam in ctc_naam or ctc_naam in naam:
                        matched.at[i, "match_op_naam"] = True
                        if matched.at[i, "suggestie"] == "":
                            matched.at[i, "suggestie"] = f"Lijkt op CTC item: '{ctc_naam}'"

    # Eindresultaat
    matched["match_gevonden"] = matched["match_op_nummer"] | matched["match_op_naam"]

    st.success(f"Matching voltooid – {matched['match_gevonden'].sum()} mogelijke matches gevonden.")
    st.dataframe(matched, use_container_width=True)

    csv = matched.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download resultaat (CSV)",
        data=csv,
        file_name="ctc_match_resultaat.csv",
        mime="text/csv"
    )
