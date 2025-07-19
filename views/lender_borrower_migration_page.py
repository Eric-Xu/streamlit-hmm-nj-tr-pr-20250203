from typing import Dict, List, Set

import altair as alt
import pandas as pd
import streamlit as st

from constants.css import GREEN_HEX, YELLOW_HEX
from pipelines.prepare_loan_data import prep_data
from utils.gui import show_default_footer, show_st_h1, show_st_h2
from utils.io import load_json
from utils.party_churn import (
    get_lender_to_gained_borrowers,
    get_lender_to_lost_borrowers,
)


def _create_horizontal_bar_chart(
    chart_data: pd.DataFrame,
) -> alt.Chart:
    color_scale = alt.Scale(domain=["lost", "gained"], range=[YELLOW_HEX, GREEN_HEX])
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
    )

    return chart


def _get_borrower_migration_all_lenders(prepped_data: List[Dict]) -> List[Dict]:

    lender_to_lost_borrowers: Dict[str, Set] = get_lender_to_lost_borrowers(
        prepped_data
    )
    lender_to_gained_borrowers: Dict[str, Set] = get_lender_to_gained_borrowers(
        prepped_data
    )
    lender_to_lost_count = {
        lender: len(borrowers) for lender, borrowers in lender_to_lost_borrowers.items()
    }
    lender_to_gained_count = {
        lender: len(borrowers)
        for lender, borrowers in lender_to_gained_borrowers.items()
    }

    borrower_migration_all_lenders: List[Dict] = []
    for lender, num in lender_to_lost_count.items():
        borrower_migration_all_lenders.append(
            {"num_borrowers": -abs(num), "lender": lender, "borrower_status": "lost"}
        )
    for lender, num in lender_to_gained_count.items():
        borrower_migration_all_lenders.append(
            {"num_borrowers": abs(num), "lender": lender, "borrower_status": "gained"}
        )

    return borrower_migration_all_lenders


def _get_borrower_migration_top_n(
    borrower_migration_all_lenders: List[Dict], top_n: int, borrower_status: str
) -> pd.DataFrame:
    migration_data_all_lenders: pd.DataFrame = pd.DataFrame(
        borrower_migration_all_lenders
    )

    # Sort the df by num_borrowers based on the borrower_status ("gained" or "lost")
    if borrower_status == "gained":
        migration_data_all_lenders["tmp_sort_col"] = migration_data_all_lenders.apply(
            lambda row: (
                row["num_borrowers"] if row["borrower_status"] == "gained" else 0
            ),
            axis=1,
        )
        migration_data_all_lenders = migration_data_all_lenders.sort_values(
            by="tmp_sort_col", ascending=False
        ).drop(columns=["tmp_sort_col"])
    else:
        migration_data_all_lenders["tmp_sort_col"] = migration_data_all_lenders.apply(
            lambda row: row["num_borrowers"] if row["borrower_status"] == "lost" else 0,
            axis=1,
        )
        migration_data_all_lenders = migration_data_all_lenders.sort_values(
            by="tmp_sort_col", ascending=True
        ).drop(columns=["tmp_sort_col"])

    # Get top_n lenders for the given borrower status.
    top_n_matching_status_records = migration_data_all_lenders.head(top_n)
    top_n_lenders = set(top_n_matching_status_records["lender"])

    # Get records of the opposing status for the top_n lenders.
    opposite_status = "lost" if borrower_status == "gained" else "gained"
    top_n_opposite_status_records = migration_data_all_lenders[
        (migration_data_all_lenders["lender"].isin(top_n_lenders))
        & (migration_data_all_lenders["borrower_status"] == opposite_status)
    ]

    # Return the number of gained and lost borrowers for the top_n lenders.
    top_n_both_status_records = pd.concat(
        [top_n_matching_status_records, top_n_opposite_status_records],
        ignore_index=True,
    )

    return top_n_both_status_records


def _show_horizontal_bar_chart(chart_data: pd.DataFrame) -> None:
    horizontal_bar_chart: alt.Chart = _create_horizontal_bar_chart(chart_data)
    st.altair_chart(horizontal_bar_chart, use_container_width=True)


def _show_horizontal_bar_chart_data(
    prepped_data: List[Dict], lenders: Set[str]
) -> None:
    lender_to_lost_borrowers: Dict[str, Set] = get_lender_to_lost_borrowers(
        prepped_data
    )
    lender_to_gained_borrowers: Dict[str, Set] = get_lender_to_gained_borrowers(
        prepped_data
    )

    lender_borrower_status: List[Dict] = []
    for lender in lenders:
        # Lost borrowers
        for borrower in lender_to_lost_borrowers.get(lender, set()):
            lender_borrower_status.append(
                {
                    "lender_name": lender,
                    "borrower_name": borrower,
                    "borrower_status": "lost",
                }
            )
        # Gained borrowers
        for borrower in lender_to_gained_borrowers.get(lender, set()):
            lender_borrower_status.append(
                {
                    "lender_name": lender,
                    "borrower_name": borrower,
                    "borrower_status": "gained",
                }
            )
    lender_borrower_status_df = pd.DataFrame(lender_borrower_status)
    lender_borrower_status_df = lender_borrower_status_df.sort_values(
        by=["lender_name", "borrower_status", "borrower_name"]
    ).reset_index(drop=True)

    st.dataframe(lender_borrower_status_df)


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

    borrower_migration_all_lenders: List[Dict] = _get_borrower_migration_all_lenders(
        prepped_data
    )

    st.write("")
    st.markdown("#### Who signed up the most borrower clients from competitors?")

    top_n_gained: int = st.slider(
        "Select the number of most-borrowers-gained records to display.", 10, 50, 25, 5
    )
    borrower_migration_top_n_gained: pd.DataFrame = _get_borrower_migration_top_n(
        borrower_migration_all_lenders, top_n_gained, "gained"
    )

    st.write("")
    st.write("")
    _show_horizontal_bar_chart(borrower_migration_top_n_gained)

    show_gained_data = st.toggle("Show Most-Borrowers-Gained Chart Data")
    if show_gained_data:
        top_n_gained_lenders = set(borrower_migration_top_n_gained["lender"].unique())
        _show_horizontal_bar_chart_data(prepped_data, top_n_gained_lenders)

    st.info(
        f"""
        ##### :material/cognition: How to Interpret the Chart
        This chart illustrates borrower gains and losses among lenders with
        the most active migration activity. A lender with significantly higher
        gains than losses demonstrates strong performance in both attracting
        business from competitors' clients and minimizing their own borrower
        churn.
        """
    )

    st.write("")
    st.markdown("#### Who lost the most past borrowers to other lenders?")

    top_n_lost: int = st.slider(
        "Select the number of most-borrowers-lost records to display.", 10, 50, 25, 5
    )
    borrower_migration_top_n_lost: pd.DataFrame = _get_borrower_migration_top_n(
        borrower_migration_all_lenders, top_n_lost, "lost"
    )

    st.write("")
    st.write("")
    _show_horizontal_bar_chart(borrower_migration_top_n_lost)

    show_lost_data = st.toggle("Show Most-Borrowers-Lost Chart Data")
    if show_lost_data:
        top_n_lost_lenders = set(borrower_migration_top_n_lost["lender"].unique())
        _show_horizontal_bar_chart_data(prepped_data, top_n_lost_lenders)

    st.info(
        f"""
        ##### :material/cognition: How to Interpret the Chart
        A large net loss of borrowers may signal misaligned offerings, evolving 
        capital market conditions, or a strategic market exit by the lender.
        """
    )

    show_default_footer()


render_page()
