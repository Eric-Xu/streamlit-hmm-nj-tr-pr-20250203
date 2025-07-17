from collections import Counter
from typing import Dict, List, Tuple

import pandas as pd
import streamlit as st
from matplotlib.figure import Figure
from pycirclize import Circos
from pycirclize.parser import Matrix

from constants.css import GRAY_HEX, GREEN_HEX
from pipelines.prepare_loan_data import prep_data
from utils.gui import show_st_h1, show_st_h2
from utils.io import load_json
from utils.party_churn import (
    get_borrower_to_last_lender,
    get_lender_to_all_borrowers,
    get_lender_to_churned_borrowers,
)

MIN_BORROWER_CHURN_THRESHOLD = 1


def _create_chord_diagram(prepped_data: List[Dict]) -> Figure:
    borrower_to_last_lender: Dict[str, str] = get_borrower_to_last_lender(prepped_data)
    lender_to_all_borrowers: Dict[str, List[str]] = get_lender_to_all_borrowers(
        prepped_data
    )
    lender_to_churned_borrowers: Dict[str, List[str]] = get_lender_to_churned_borrowers(
        lender_to_all_borrowers, borrower_to_last_lender
    )
    fromto_lenders: List[Tuple[str, str]] = []
    for from_lender, churned_borrowers in lender_to_churned_borrowers.items():
        for churned_borrower in churned_borrowers:
            to_lender = borrower_to_last_lender.get(churned_borrower)
            if to_lender and to_lender != from_lender:
                fromto_lenders.append((from_lender, to_lender))

    # Count occurrences of each (from_lender, to_lender) pair
    fromto_counter = Counter(fromto_lenders)
    fromto_lender_w_counts: List[List[str | int]] = [
        [from_lender, to_lender, count]
        for (from_lender, to_lender), count in fromto_counter.items()
    ]

    # Remove records to reduce chart clutter
    fromto_lender_w_min_counts: List[List[str | int]] = [
        row
        for row in fromto_lender_w_counts
        if int(row[2]) > MIN_BORROWER_CHURN_THRESHOLD
    ]

    fromto_table_df = pd.DataFrame(
        fromto_lender_w_min_counts,
        columns=["from", "to", "value"],
    )
    matrix = Matrix.parse_fromto_table(fromto_table_df)

    # Build cmap dict mapping each unique lender to GREEN_HEX
    segment_labels = set(str(row[0]) for row in fromto_lender_w_min_counts) | set(
        str(row[1]) for row in fromto_lender_w_min_counts
    )
    cmap = {label: GREEN_HEX for label in segment_labels}

    circos = Circos.chord_diagram(
        matrix,
        space=4,
        cmap=cmap,
        ticks_interval=2,
        label_kws=dict(alpha=0.0),  # Hide default sector.text()
        link_kws=dict(direction=1),
        ticks_kws=dict(outer=True, text_kws=dict(color=GRAY_HEX)),
    )

    # Create annotation labels to avoid overlapping texts.
    for sector in circos.sectors:
        for track in sector.tracks:
            label_pos = sector.center
            track.annotate(x=label_pos, label=sector.name, label_size=10, shorten=100)

    fig: Figure = circos.plotfig()

    return fig


def _show_chord_diagram(prepped_data: List[Dict]) -> None:
    chord_diagram: Figure = _create_chord_diagram(prepped_data)
    st.pyplot(chord_diagram, use_container_width=True)

    st.info(
        f"""
        ##### :material/cognition: How to Interpret the Chart
        """
    )


def _show_introduction() -> None:
    st.write(
        """
        A "churned borrower" is defined as someone who previously received one or
        more loans from the lender but has not returned for additional financing 
        on their latest project.
    """
    )


def render_page() -> None:
    show_st_h1("Lender Analysis")
    show_st_h2("Borrower Migration", w_divider=True)

    prepped_data_file_path: str = prep_data()
    prepped_data: List[Dict] = load_json(prepped_data_file_path)

    st.write("")
    _show_introduction()

    st.markdown("#### Version 2: Where did churned borrowers go for new loans?")

    _show_chord_diagram(prepped_data)

    # st.write("")
    # st.write("")
    # selected_lender: str = _show_selectbox(prepped_data)

    # st.write("")
    # st.write("")
    # _show_metrics_selected_data(prepped_data, selected_lender)

    # st.write("")
    # _show_df(prepped_data, selected_lender)


render_page()
