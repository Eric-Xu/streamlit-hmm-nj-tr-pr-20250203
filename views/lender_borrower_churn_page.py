from collections import Counter
from typing import Dict, List, Tuple

import altair as alt
import pandas as pd
import streamlit as st
from matplotlib.figure import Figure
from pycirclize import Circos, config
from pycirclize.parser import Matrix

from constants.css import GRAY_HEX, RED_HEX
from pipelines.prepare_loan_data import prep_data
from utils.gui import show_default_footer, show_st_h1, show_st_h2
from utils.io import load_json
from utils.party_churn import (
    get_borrower_to_last_lender,
    get_lender_to_all_borrowers,
    get_lender_to_churned_borrowers,
)

HIDE_SCATTERPLOT_LINE_THRESHOLD = 10


def _get_lender_churn_scatter_data(
    prepped_data: List[Dict], lender_to_churned_borrowers: Dict[str, List[str]]
) -> pd.DataFrame:
    """
    Returns a DataFrame with columns: lender, lender_num_loans, num_churned_borrowers
    for use in the churn scatter plot.
    """
    lender_points = []
    for lender, churned_borrowers in lender_to_churned_borrowers.items():
        # Find a record for this lender to get lender_num_loans
        lender_records = [
            rec for rec in prepped_data if rec.get("lenderName") == lender
        ]
        if not lender_records:
            continue
        try:
            lender_num_loans = lender_records[0].get("lender_num_loans")
        except (TypeError, ValueError):
            lender_num_loans = None
        y_val = len(churned_borrowers)
        if lender_num_loans is not None:
            lender_points.append(
                {
                    "lender": lender,
                    "lender_num_loans": lender_num_loans,
                    "num_churned_borrowers": y_val,
                }
            )

    return pd.DataFrame(lender_points)


def _get_borrower_to_all_lenders(prepped_data: List[Dict]) -> Dict[str, List[str]]:
    """
    For each borrower (buyerName), return a list of unique lender names they've used.
    """
    borrower_to_lenders: Dict[str, set] = {}
    for record in prepped_data:
        borrower = record.get("buyerName")
        lender = record.get("lenderName")
        if not borrower or not lender:
            continue
        if borrower not in borrower_to_lenders:
            borrower_to_lenders[borrower] = set()
        borrower_to_lenders[borrower].add(lender)
    # Convert sets to lists
    return {
        borrower: list(lenders) for borrower, lenders in borrower_to_lenders.items()
    }


def _get_borrower_to_total_volume(prepped_data: List[Dict]) -> Dict[str, int]:
    """
    For each borrower (buyerName), return the sum of loanAmount for that borrower in prepped_data.
    """
    borrower_to_total: Dict[str, float] = {}
    for record in prepped_data:
        borrower = record.get("buyerName")
        loan_amount = record.get("loanAmount")
        if loan_amount in (None, ""):
            continue
        try:
            loan_amount = float(loan_amount)
        except (TypeError, ValueError):
            continue
        if not borrower:
            continue
        if borrower not in borrower_to_total:
            borrower_to_total[borrower] = 0.0
        borrower_to_total[borrower] += loan_amount
    # Convert to int for display
    return {k: int(v) for k, v in borrower_to_total.items()}


def _show_df(prepped_data: List[Dict], lender: str) -> None:
    selected_data: List[Dict] = [
        d for d in prepped_data if d.get("lenderName", "") == lender
    ]
    if not selected_data:
        return

    borrower_to_last_lender: Dict[str, str] = get_borrower_to_last_lender(prepped_data)
    borrower_to_all_lenders: Dict[str, List[str]] = _get_borrower_to_all_lenders(
        prepped_data
    )
    borrower_to_total_volume: Dict[str, int] = _get_borrower_to_total_volume(
        prepped_data
    )

    # Add these values to each record in prepped_data by matching borrower name
    for record in prepped_data:
        borrower = record.get("buyerName")
        borrower_key = borrower if isinstance(borrower, str) and borrower else ""
        last_lender = borrower_to_last_lender.get(borrower_key, "")
        record["has_churned"] = "Yes" if last_lender != lender else ""
        record["last_lender"] = last_lender
        record["all_lenders"] = " | ".join(
            borrower_to_all_lenders.get(borrower_key, [])
        )
        record["total_volume"] = borrower_to_total_volume.get(borrower_key, 0)

    df = pd.DataFrame(selected_data)

    columns_to_keep = [
        "buyerName",
        "borrower_num_loans",
        "total_volume",
        "has_churned",
        "last_lender",
        "all_lenders",
    ]
    df = df[columns_to_keep]
    df = df.drop_duplicates()

    st.dataframe(
        df,
        use_container_width=True,
        column_config={
            "buyerName": st.column_config.TextColumn("Borrower Name"),
            "borrower_num_loans": st.column_config.NumberColumn("Number of Loans"),
            "total_volume": st.column_config.NumberColumn(
                "Total Volume", format="dollar", width="medium"
            ),
            "has_churned": st.column_config.TextColumn("Has Churned"),
            "last_lender": st.column_config.TextColumn("Last Lender"),
            "all_lenders": st.column_config.TextColumn("Lenders Used"),
        },
    )


def _show_introduction() -> None:
    st.write(
        """
        A "churned borrower" is defined as someone who previously received one or
        more loans from the lender but has not returned for additional financing 
        on their latest project.
    """
    )


def _show_metrics_selected_data(prepped_data: List[Dict], lender: str) -> None:
    selected_data: List[Dict] = [
        d for d in prepped_data if d.get("lenderName", "") == lender
    ]
    if not selected_data:
        return
    else:
        borrower_to_last_lender: Dict[str, str] = get_borrower_to_last_lender(
            prepped_data
        )
        lender_to_all_borrowers: Dict[str, List[str]] = get_lender_to_all_borrowers(
            prepped_data
        )
        lender_to_churned_borrowers: Dict[str, List[str]] = (
            get_lender_to_churned_borrowers(
                lender_to_all_borrowers, borrower_to_last_lender
            )
        )
        all_borrowers = set(lender_to_all_borrowers.get(lender, []))
        churned_borrowers = set(lender_to_churned_borrowers.get(lender, []))
        num_all_borrowers = len(all_borrowers)
        num_churned_borrowers = len(churned_borrowers)
        churn_rate = (
            round((num_churned_borrowers / num_all_borrowers) * 100, 1)
            if num_all_borrowers > 0
            else 0
        )

    col1, col2 = st.columns(2)
    col1.metric(
        "Churned Borrowers", f"{num_churned_borrowers}/{num_all_borrowers}", border=True
    )
    col2.metric("Churn Rate", f"{churn_rate}%", border=True)


def _show_scatterplot(prepped_data: List[Dict]) -> None:
    """
    Recently churned borrowers (scatterplot of "num recently churned" to "lender num loans").
        - Given a lender, list any recently churned borrowers (last loan went to a different lender)
    """
    borrower_to_last_lender: Dict[str, str] = get_borrower_to_last_lender(prepped_data)
    lender_to_all_borrowers: Dict[str, List[str]] = get_lender_to_all_borrowers(
        prepped_data
    )
    lender_to_churned_borrowers: Dict[str, List[str]] = get_lender_to_churned_borrowers(
        lender_to_all_borrowers, borrower_to_last_lender
    )

    # Prepare data for scatter plot: x = lender_num_loans, y = number of churned borrowers
    chart_data = _get_lender_churn_scatter_data(
        prepped_data, lender_to_churned_borrowers
    )
    if not chart_data.empty:
        scatter = (
            alt.Chart(chart_data)
            .mark_circle(size=100, color=RED_HEX)
            .encode(
                x=alt.X("lender_num_loans", title="Number of Loans"),
                y=alt.Y("num_churned_borrowers", title="Number of Churned Borrowers"),
                tooltip=["lender", "lender_num_loans", "num_churned_borrowers"],
            )
            .properties(width="container")
        )
        if len(chart_data) > HIDE_SCATTERPLOT_LINE_THRESHOLD:
            line = (
                alt.Chart(chart_data)
                .transform_regression("lender_num_loans", "num_churned_borrowers")
                .mark_line(color=GRAY_HEX)
                .encode(x="lender_num_loans", y="num_churned_borrowers")
            )
            chart = alt.layer(line, scatter)
        else:
            chart = scatter

        chart = chart.properties(
            title={
                "text": "Comparison of Borrower Churn Among Lenders",
                "anchor": "middle",
            }
        )
        st.altair_chart(chart, use_container_width=True)

    st.info(
        f"""
        ##### :material/cognition: How to Interpret the Chart
        Each point represents a lender, with its position corresponding to the 
        total number of loans on the X-axis and the number of borrowers who have 
        churned on the Y-axis. For datasets with 10 or more points, a line of 
        best fit is drawn. The farther a point lies above the line, the higher 
        its churn rate relative to other lenders, and vice versa.
        """
    )


def _show_selectbox(prepped_data: List[Dict]) -> str:
    lenders = sorted(
        set(d.get("lenderName", "") for d in prepped_data if d.get("lenderName", ""))
    )
    option: str = st.selectbox(
        "Enter a lender’s name to view their churned borrowers, if any.",
        lenders,
    )

    return option


def render_page() -> None:
    show_st_h1("Lender Analysis")
    show_st_h2("Borrower Churn Rate", w_divider=True)

    prepped_data_file_path: str = prep_data()
    prepped_data: List[Dict] = load_json(prepped_data_file_path)

    st.write("")
    _show_introduction()

    st.write("")
    st.write("")
    _show_scatterplot(prepped_data)

    st.write("")
    st.write("")
    selected_lender: str = _show_selectbox(prepped_data)

    st.write("")
    st.write("")
    _show_metrics_selected_data(prepped_data, selected_lender)

    st.write("")
    _show_df(prepped_data, selected_lender)

    show_default_footer()


render_page()
