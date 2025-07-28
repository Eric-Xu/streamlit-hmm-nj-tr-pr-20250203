import math
from typing import Dict, List, Tuple

import pandas as pd
import streamlit as st

from constants.dataset import LOCATION
from pipelines.prepare_loan_data import prep_data
from utils.gui import show_default_footer, show_st_h1, show_st_h2, show_st_info
from utils.io import load_json
from utils.lender import get_lender_to_loan_amount_bins
from utils.market_share_stacked_bar import (
    BIN_EDGE_TO_LABEL,
    LABEL_SEPARATOR,
    get_edge_range,
    show_lender_market_share_stacked_bar,
)

CITY_NUM_LOANS_MIN_THREASHOLD = 20
BIN_NUM_LOANS_MIN_THREASHOLD = 10
RADIO_MONOPOLY_SEGMENT = "Top 10 Most Monopolized Market Segments"
RADIO_DIVERSITY_SEGMENT = "Top 10 Market Segments by Lender Diversity"
RADIO_ALL_SEGMENT = "All Market Segments"


def _get_above_threshold_df(df: pd.DataFrame) -> pd.DataFrame:
    # Group by city and count the number of loans in each city
    city_loan_counts = df.groupby("city").size()
    city_loan_counts.name = "loan_count"
    city_loan_counts = city_loan_counts.reset_index()

    # Split city_loan_counts into two DataFrames based on the threshold
    below_threshold = city_loan_counts[
        city_loan_counts["loan_count"] < CITY_NUM_LOANS_MIN_THREASHOLD
    ]
    above_or_equal_threshold = city_loan_counts[
        city_loan_counts["loan_count"] >= CITY_NUM_LOANS_MIN_THREASHOLD
    ]

    print(f"Disregard cities with loan counts < {CITY_NUM_LOANS_MIN_THREASHOLD}")
    for _, row in below_threshold.iterrows():
        print(f"{row['city']}: {row['loan_count']}")

    return above_or_equal_threshold


def _get_selected_score_records(
    score_records: List[Dict], selected_min_num_loans: int, market_category: str
) -> List[Dict]:
    filtered_records = [
        record
        for record in score_records
        if record["bin_num_loans"] >= selected_min_num_loans
    ]

    if market_category == RADIO_MONOPOLY_SEGMENT:
        # Sort by highest standard deviation (most monopolized) and take top 10
        sorted_records = sorted(
            filtered_records, key=lambda x: x["bin_num_loans_pct_std_dev"], reverse=True
        )
        return sorted_records[:10]
    elif market_category == RADIO_DIVERSITY_SEGMENT:
        # Sort by lowest standard deviation (most diverse) and take top 10
        sorted_records = sorted(
            filtered_records, key=lambda x: x["bin_num_loans_pct_std_dev"]
        )
        return sorted_records[:10]
    else:
        order_map = {
            "$5M - $10M": 1,
            "$2.5M - $5M": 2,
            "$1M - $2.5M": 3,
            "$500K - $1M": 4,
            "$250K - $500K": 5,
            "$100K - $250K": 6,
            "$50K - $100K": 7,
            "$0 - $50K": 8,
        }
        sorted_records = sorted(
            filtered_records, key=lambda x: order_map.get(x["loan_amount_bin"], 999)
        )
        return sorted_records


def _get_score_records(
    df: pd.DataFrame, above_threshold_cities: List[str]
) -> List[Dict]:
    # For each city in above_or_equal_threshold, create a new DataFrame with rows from df that match the city
    city_to_df: Dict[str, pd.DataFrame] = {}
    for city, city_df in df[df["city"].isin(above_threshold_cities)].groupby("city"):
        city_to_df[str(city)] = city_df.copy()

    # Ensure bin_edges and bin_labels are in ascending order for pd.cut
    bin_edges: List[int] = [0] + sorted(BIN_EDGE_TO_LABEL.keys())
    bin_labels: List[str] = [
        BIN_EDGE_TO_LABEL[edge] for edge in sorted(BIN_EDGE_TO_LABEL.keys())
    ]

    # for each city:
    score_records: List[Dict] = []
    for city, city_df in city_to_df.items():
        lender_to_loan_amount_bins: pd.DataFrame = get_lender_to_loan_amount_bins(
            city_df, bin_edges, bin_labels
        )
        # Add a column 'bin_num_loans' that sums num_loans for each loan_amount_bin
        bin_num_loans = lender_to_loan_amount_bins.groupby(
            "loan_amount_bin", observed=True
        )["num_loans"].transform("sum")
        lender_to_loan_amount_bins["bin_num_loans"] = bin_num_loans

        lender_to_loan_amount_bins["lender_num_loans_pct"] = (
            lender_to_loan_amount_bins["num_loans"]
            / lender_to_loan_amount_bins["bin_num_loans"]
            * 100
        )

        lender_to_loan_amount_bins = lender_to_loan_amount_bins[
            lender_to_loan_amount_bins["bin_num_loans"] >= BIN_NUM_LOANS_MIN_THREASHOLD
        ]

        # Calculate the standard deviation of lender_num_loans_pct for each loan_amount_bin
        bin_num_loans_pct_std_dev = lender_to_loan_amount_bins.groupby(
            "loan_amount_bin", observed=True
        )["lender_num_loans_pct"].transform("std")
        lender_to_loan_amount_bins["bin_num_loans_pct_std_dev"] = (
            bin_num_loans_pct_std_dev
        )

        # For each unique loan_amount_bin, add a row with city, loan_amount_bin, and bin_num_loans_pct_std_dev
        for bin_value, group in lender_to_loan_amount_bins.groupby(
            "loan_amount_bin", observed=True
        ):
            if group.empty:
                continue
            std_dev = group["bin_num_loans_pct_std_dev"].iloc[0]
            bin_num_loans = group["bin_num_loans"].iloc[0]
            score_records.append(
                {
                    "city": city,
                    "loan_amount_bin": bin_value,
                    "bin_num_loans": bin_num_loans,
                    "bin_num_loans_pct_std_dev": std_dev,
                }
            )

    return score_records


def _get_stacked_bar_data(df: pd.DataFrame, score_records: List[Dict]) -> pd.DataFrame:
    """
    Returns a DataFrame with the following columns:
    - lender: str ("KIAVI FUNDING INC)
    - loan_amount_bin: str ("DOVER  |  $100K - $250K")
    - num_loans: int (10)
    """
    amount_bin_level_dfs: List[pd.DataFrame] = []
    for record in score_records:
        city: str = record["city"]
        loan_amount_bin: str = record["loan_amount_bin"]
        city_level_df: pd.DataFrame = df[df["city"] == city]
        joined_bin_label = f"{city}{LABEL_SEPARATOR}{loan_amount_bin}"
        bin_edges: Tuple[int, int] = get_edge_range(loan_amount_bin)
        bin_level_df: pd.DataFrame = get_lender_to_loan_amount_bins(
            city_level_df, list(bin_edges), [joined_bin_label]
        )
        amount_bin_level_dfs.append(bin_level_df)

    chart_df: pd.DataFrame = pd.concat(amount_bin_level_dfs, ignore_index=True)

    return chart_df


def _show_info_stacked_bar(selected_category: str) -> None:
    if selected_category == RADIO_MONOPOLY_SEGMENT:
        text = f'"{selected_category}" are the top 10 market segments with the highest market concentration.'
    elif selected_category == RADIO_DIVERSITY_SEGMENT:
        text = f"'{selected_category}' are the top 10 market segments with the highest lender diversity."
    else:
        text = f"'{selected_category}' are all market segments."

    st.info(
        f"""
        ##### :material/cognition: How to Interpret the Chart
        {text}
        """
    )


def _show_introduction() -> None:
    st.write(
        """
        TODO: Add introduction
    """
    )


def _show_df(selected_score_records: List[Dict]) -> None:
    st.dataframe(
        selected_score_records,
        use_container_width=True,
        column_config={
            "city": st.column_config.TextColumn("City"),
            "loan_amount_bin": st.column_config.TextColumn("Loan Amount Bin"),
            "bin_num_loans": st.column_config.NumberColumn("Number of Loans"),
            "bin_num_loans_pct_std_dev": st.column_config.NumberColumn(
                "Market Monopoly Score", format="%.2f"
            ),
        },
    )


def _show_slider(score_records: List[Dict]) -> int:
    max_bin_num_loans: int = max(record["bin_num_loans"] for record in score_records)
    max_value: int = math.ceil(max_bin_num_loans / 10) * 10
    min_value: int = BIN_NUM_LOANS_MIN_THREASHOLD
    default_value: int = min_value
    if max_value <= 20:
        step: int = 1
    elif max_value <= 100:
        step: int = 5
    elif max_value <= 500:
        step: int = 10
    else:
        step: int = 50

    selected_num_loans: int = st.slider(
        "Select the minimum number of loans per market segment.",
        min_value,
        max_value,
        default_value,
        step,
    )

    return selected_num_loans


def _show_stacked_bar(chart_df: pd.DataFrame) -> None:
    sorted_bin_labels: List[str] = list(chart_df["loan_amount_bin"].unique())
    height = max(70 * len(sorted_bin_labels), 160)
    y_title = None
    y_label_limit = 300

    show_lender_market_share_stacked_bar(
        chart_df, sorted_bin_labels, height, y_title, y_label_limit
    )


def render_page():
    show_st_h1("Market Analysis")
    show_st_h2(f"Power Concentration - {LOCATION}", w_divider=True)

    prepped_data_file_path: str = prep_data()
    prepped_data: List[Dict] = load_json(prepped_data_file_path)

    st.write("")
    _show_introduction()

    df = pd.DataFrame(prepped_data)
    df["loanAmount"] = pd.to_numeric(df["loanAmount"], errors="coerce")

    above_threshold_df: pd.DataFrame = _get_above_threshold_df(df)
    above_threshold_cities: List[str] = list(above_threshold_df["city"])
    score_records: List[Dict] = _get_score_records(df, above_threshold_cities)

    selected_category: str = st.radio(
        "Select the category to display.",
        [RADIO_MONOPOLY_SEGMENT, RADIO_DIVERSITY_SEGMENT, RADIO_ALL_SEGMENT],
    )
    selected_min_num_loans: int = _show_slider(score_records)

    selected_score_records: List[Dict] = _get_selected_score_records(
        score_records, selected_min_num_loans, selected_category
    )
    if not selected_score_records:
        show_st_info("no_data_selected")
        show_default_footer()
        return

    st.write("")
    st.write("")
    chart_df: pd.DataFrame = _get_stacked_bar_data(df, selected_score_records)
    _show_stacked_bar(chart_df)

    show_chart_data = st.toggle("Show Chart Data")
    if show_chart_data:
        _show_df(selected_score_records)

    _show_info_stacked_bar(selected_category)

    show_default_footer()


render_page()
