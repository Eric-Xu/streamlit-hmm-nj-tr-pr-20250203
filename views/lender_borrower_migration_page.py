from typing import Dict, List, Set, Tuple

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st
from matplotlib.figure import Figure
from pycirclize import Circos
from pycirclize.parser import Matrix

from constants.css import BLUE_HEX, GRAY_HEX, GREEN_HEX, RED_HEX
from pipelines.prepare_loan_data import prep_data
from utils.gui import show_st_h1, show_st_h2
from utils.io import load_json
from utils.party_churn import get_borrower_fromto_lenders, get_fromto_lenders_w_counts

MIN_BORROWER_CHURN_THRESHOLD = 1


def _create_chord_diagram(prepped_data: List[Dict]) -> Figure:
    # Count occurrences of each (from_lender, to_lender) pair
    fromto_lenders_w_counts: List[Tuple[str, str, int]] = get_fromto_lenders_w_counts(
        prepped_data
    )

    # Remove records to reduce chart clutter
    fromto_lender_w_min_counts: List[Tuple[str, str, int]] = [
        row
        for row in fromto_lenders_w_counts
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


def _create_horizontal_bar_chart(chart_data: pd.DataFrame) -> alt.Chart:
    color_scale = alt.Scale(domain=["lost", "gained"], range=[RED_HEX, BLUE_HEX])
    chart = (
        alt.Chart(chart_data)
        .mark_bar()
        .encode(
            x=alt.X("num_borrowers:Q", title="Number of Borrowers Lost/Gained"),
            y=alt.Y("lender:N", sort=None, title=None, axis=alt.Axis(labelLimit=0)),
            color=alt.Color("borrower_status:N", scale=color_scale, legend=None),
            tooltip=[
                alt.Tooltip("num_borrowers:Q", title="num_borrowers"),
                alt.Tooltip("lender:N", title="lender"),
                alt.Tooltip("borrower_status:N", title="borrower_status"),
            ],
        )
        .properties(
            title=alt.TitleParams(text="Lenders with the Highest Borrower Migration")
        )
    )

    return chart


def _get_horizontal_bar_chart_data(
    prepped_data: List[Dict], top_n=None
) -> pd.DataFrame:
    borrower_fromto_lenders: List[Tuple[str, str, str]] = get_borrower_fromto_lenders(
        prepped_data
    )

    # Calculate lost and gained borrower counts per lender (unique borrowers only)
    lender_to_lost_count: Dict[str, int] = {}
    lender_to_gained_count: Dict[str, int] = {}
    lender_to_lost_borrowers: Dict[str, Set] = {}
    lender_to_gained_borrowers: Dict[str, Set] = {}
    for churned_borrower, from_lender, to_lender in borrower_fromto_lenders:
        if from_lender not in lender_to_lost_borrowers:
            lender_to_lost_borrowers[from_lender] = set()
        if to_lender not in lender_to_gained_borrowers:
            lender_to_gained_borrowers[to_lender] = set()
        lender_to_lost_borrowers[from_lender].add(churned_borrower)
        lender_to_gained_borrowers[to_lender].add(churned_borrower)
    lender_to_lost_count = {
        lender: len(borrowers) for lender, borrowers in lender_to_lost_borrowers.items()
    }
    lender_to_gained_count = {
        lender: len(borrowers)
        for lender, borrowers in lender_to_gained_borrowers.items()
    }

    data: List[Dict] = []
    for lender, num in lender_to_lost_count.items():
        data.append(
            {"num_borrowers": -abs(num), "lender": lender, "borrower_status": "lost"}
        )
    for lender, num in lender_to_gained_count.items():
        data.append(
            {"num_borrowers": abs(num), "lender": lender, "borrower_status": "gained"}
        )
    data_all: pd.DataFrame = pd.DataFrame(data)
    st.write(data_all)

    # Sort so that the lender with the highest gained num_borrowers comes first
    data_all["tmp_gained"] = data_all.apply(
        lambda row: row["num_borrowers"] if row["borrower_status"] == "gained" else 0,
        axis=1,
    )
    data_all = data_all.sort_values(by="tmp_gained", ascending=False)
    data_all = data_all.drop(columns=["tmp_gained"])

    if top_n:
        data_top_n_mostly_gained_records = data_all.head(top_n)
        top_lenders = set(data_top_n_mostly_gained_records["lender"])
        data_top_n_lost_records = data_all[
            (data_all["lender"].isin(top_lenders))
            & (data_all["borrower_status"] == "lost")
        ]
        data = pd.concat(
            [data_top_n_mostly_gained_records, data_top_n_lost_records],
            ignore_index=True,
        )
    else:
        data = data_all

    return data


def _show_chord_diagram(prepped_data: List[Dict]) -> None:
    chord_diagram: Figure = _create_chord_diagram(prepped_data)
    st.pyplot(chord_diagram, use_container_width=True)

    st.info(
        f"""
        ##### :material/cognition: How to Interpret the Chart
        TODO
        """
    )


def _show_horizontal_bar_chart(prepped_data: List[Dict]) -> None:
    top_n = 20
    chart_data_top_n: pd.DataFrame = _get_horizontal_bar_chart_data(prepped_data, top_n)

    horizontal_bar_chart: alt.Chart = _create_horizontal_bar_chart(chart_data_top_n)
    st.altair_chart(horizontal_bar_chart, use_container_width=True)

    st.info(
        f"""
        ##### :material/cognition: How to Interpret the Chart
        This chart aims to illustrate each lender's net borrower migration. A 
        lender with significantly higher gains than losses demonstrates strong 
        performance in both attracting business from competitors' clients and
        minimizing their own borrower churn.
        """
    )

    on = st.toggle("Show Chart Data")

    if on:
        st.dataframe(chart_data_top_n)


def _show_introduction() -> None:
    st.write(
        """
        “Borrower migration” is defined as the acquisition of a borrower who left 
        another lender, or when a borrower seeks financing for their latest project
        from a different lender.
    """
    )


def render_page() -> None:
    show_st_h1("Lender Analysis")
    show_st_h2("Borrower Migration", w_divider=True)

    prepped_data_file_path: str = prep_data()
    prepped_data: List[Dict] = load_json(prepped_data_file_path)

    st.write("")
    _show_introduction()

    st.write("")
    st.write("")
    _show_horizontal_bar_chart(prepped_data)

    st.write("")
    st.markdown("#### Where did churned borrowers go for new loans?")

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
