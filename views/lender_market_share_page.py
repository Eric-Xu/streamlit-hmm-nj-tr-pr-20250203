from typing import Dict, List, Tuple

import altair as alt
import pandas as pd
import streamlit as st

from constants.css import BLUE_HEX, GREEN_HEX
from constants.dataset import LOCATION
from pipelines.prepare_loan_data import prep_data
from utils.formatting import to_currency
from utils.gui import show_default_footer, show_st_h1, show_st_h2, show_st_info
from utils.io import load_json
from utils.party_to_loan_relationship import show_relationship_network_graph


def _get_bar_chart_data(
    df: pd.DataFrame, bin_edges: List[int], bin_labels: List[str]
) -> pd.DataFrame:
    # Assign bins to each loan
    df["loan_amount_bin"] = pd.cut(
        df["loanAmount"], bins=bin_edges, labels=bin_labels, right=False
    )
    # Group by lender and bin, count number of loans
    grouped = (
        df.groupby(["lenderName", "loan_amount_bin"], observed=True)
        .size()
        .reset_index()
    )
    grouped = grouped.rename(columns={0: "num_loans", "lenderName": "lender"})

    return grouped


def _get_bar_chart_edges_labels(
    df: pd.DataFrame, required_item_count: int
) -> Tuple[List[int], List[str]]:
    bin_edge_to_mid_label = {
        50_000: "$0 - $50K",
        100_000: "$50K - $100K",
        250_000: "$100K - $250K",
        500_000: "$250K - $500K",
        1_000_000: "$500K - $1M",
        2_000_000: "$1M - $2M",
        5_000_000: "$2M - $5M",
        10_000_000: "$5M - $10M",
    }
    bin_edge_to_under_label = {
        50_000: "Under $50K",
        100_000: "Under $100K",
        250_000: "Under $250K",
        500_000: "Under $500K",
        1_000_000: "Under $1M",
    }
    bin_edge_to_over_label = {
        250_000: "Over $250K",
        500_000: "Over $250K",
        1_000_000: "Over $500K",
        2_000_000: "Over $1M",
        5_000_000: "Over $2M",
        10_000_000: "Over $5M",
    }

    min_edge_value = _get_min_bin_edge(
        df,
        list(bin_edge_to_under_label.keys()),
        required_item_count,
    )
    max_edge_value = _get_max_bin_edge(
        df,
        list(bin_edge_to_over_label.keys()),
        required_item_count,
    )

    prepped_bin_edge_to_label: Dict[int, str] = {
        k: v
        for k, v in bin_edge_to_mid_label.items()
        if k >= min_edge_value and k <= max_edge_value
    }

    if min_edge_value in prepped_bin_edge_to_label:
        prepped_bin_edge_to_label[min_edge_value] = bin_edge_to_under_label[
            min_edge_value
        ]
    if max_edge_value in prepped_bin_edge_to_label:
        prepped_bin_edge_to_label[max_edge_value] = bin_edge_to_over_label[
            max_edge_value
        ]

    prepped_bin_edge_to_label = dict(sorted(prepped_bin_edge_to_label.items()))
    prepped_bin_labels: List[str] = list(prepped_bin_edge_to_label.values())
    prepped_bin_edges: List[int] = [0] + list(prepped_bin_edge_to_label.keys())

    return prepped_bin_edges, prepped_bin_labels


def _get_df_data(
    df: pd.DataFrame, top_n_lenders_by_num_loans: List[str]
) -> pd.DataFrame:
    total_num_loans = df["loanAmount"].count()
    total_volume = df["loanAmount"].sum()

    # Filter df to only top N lenders by number of loans
    filtered_df = df[df["lenderName"].isin(top_n_lenders_by_num_loans)]

    # Aggregate metrics for each lender
    grouped_df = (
        filtered_df.groupby("lenderName")
        .agg(
            num_loans=("loanAmount", "count"),
            volume=("loanAmount", "sum"),
            avg_loan_amount=("loanAmount", "mean"),
        )
        .reset_index()
        .rename(columns={"lenderName": "lender"})
    )

    grouped_df["market_share_num_loans"] = (
        grouped_df["num_loans"] / total_num_loans * 100
    )
    grouped_df["market_share_volume"] = grouped_df["volume"] / total_volume * 100

    return grouped_df


def _get_max_bin_edge(df: pd.DataFrame, bin_edges: List[int], min_count: int) -> int:
    sorted_edges = sorted(bin_edges, reverse=True)
    for i, edge in enumerate(sorted_edges):
        count = (df["loanAmount"] >= edge).sum()
        if count > min_count:
            if i == 1:
                return sorted_edges[0]
            else:
                return sorted_edges[i - 1]

    return sorted_edges[-2]


def _get_min_bin_edge(df: pd.DataFrame, bin_edges: List[int], min_count: int) -> int:
    sorted_edges = sorted(bin_edges)
    for edge in bin_edges:
        count = (df["loanAmount"] < edge).sum()
        if count > min_count:
            return edge

    return sorted_edges[-1]


def _get_selected_data(prepped_data: List[Dict], slider_data: Dict) -> List[Dict]:
    user_min_num_loans: int = slider_data["user_min_num_loans"]
    user_max_num_loans: int = slider_data["user_max_num_loans"]

    selected_data: List[Dict] = list()
    for borrower_activity in prepped_data:
        num_loans: int = borrower_activity.get("lender_num_loans", 0)
        if num_loans >= user_min_num_loans and num_loans <= user_max_num_loans:
            selected_data.append(borrower_activity)

    return selected_data


def _show_bar_chart(df: pd.DataFrame) -> None:
    required_item_count = 5

    bin_edges, bin_labels = _get_bar_chart_edges_labels(df, required_item_count)

    source: pd.DataFrame = _get_bar_chart_data(df, bin_edges, bin_labels)

    chart = (
        alt.Chart(source)
        .mark_bar()
        .encode(
            x=alt.X("sum(num_loans)", title="Total # of Loans").stack("normalize"),
            y=alt.Y(
                "loan_amount_bin",
                title="Loan Amount",
                sort=list(reversed(bin_labels)),  # descending order
            ),
            color=alt.Color("lender", legend=None),
            tooltip=[
                alt.Tooltip("num_loans", title="Total # of Loans"),
                alt.Tooltip("lender", title="Lender"),
            ],
        )
        .properties(height=500)
    )
    st.altair_chart(chart, use_container_width=True)

    st.info(
        f"""
        ##### :material/cognition: How to Interpret the Chart
        This chart conveys the competitive landscape—measured by the number of 
        lenders—in each loan amount tier (chart row). A higher density of lines 
        indicates more lenders originating loans. A disproportionately large solid 
        segment in a row means one lender dominates that tier.
        """
    )


def _show_df_introduction(top_n_df: pd.DataFrame) -> None:
    column_order = [
        "lender",
        "num_loans",
        "volume",
        "market_share_num_loans",
        "market_share_volume",
        "avg_loan_amount",
    ]
    top_n_df = top_n_df[column_order]
    top_n_df = top_n_df.sort_values(by="num_loans", ascending=False).reset_index(
        drop=True
    )

    st.dataframe(
        top_n_df,
        use_container_width=True,
        column_config={
            "avg_loan_amount": st.column_config.NumberColumn(
                "Average Loan Amount", format="dollar"
            ),
            "lender": st.column_config.TextColumn(
                "Lender",
            ),
            "market_share_num_loans": st.column_config.NumberColumn(
                "Market Share (# Loans)", format="%.1f%%"
            ),
            "market_share_volume": st.column_config.NumberColumn(
                "Market Share (Volume)", format="%.1f%%"
            ),
            "num_loans": st.column_config.NumberColumn("# Loans"),
            "volume": st.column_config.NumberColumn("Volume", format="dollar"),
        },
    )


def _show_df_network_graph(selected_data: List[Dict]) -> None:
    df = pd.DataFrame(selected_data)

    columns_to_keep = ["lenderName", "buyerName", "loanAmount"]
    df = df[columns_to_keep]
    df["loanAmount"] = pd.to_numeric(df["loanAmount"], errors="coerce")

    st.dataframe(
        df,
        use_container_width=True,
        column_config={
            "lenderName": st.column_config.TextColumn("Lender Name", width="medium"),
            "buyerName": st.column_config.TextColumn("Borrower Name", width="medium"),
            "loanAmount": st.column_config.NumberColumn(
                "Loan Amount", width="small", format="dollar"
            ),
        },
    )


def _show_donut_chart(top_lender_pct: float, title: str) -> None:
    source = pd.DataFrame(
        {
            "category": ["(a) Top 10 Lenders", "(b) Others"],
            "value": [
                top_lender_pct,
                100 - top_lender_pct,
            ],
        }
    )

    chart = (
        alt.Chart(source)
        .mark_arc(innerRadius=60)
        .encode(
            theta="value",
            color=alt.Color(
                "category:N",
                scale=alt.Scale(
                    domain=["(a) Top 10 Lenders", "(b) Others"],
                    range=[GREEN_HEX, BLUE_HEX],
                ),
                legend=alt.Legend(
                    orient="bottom",
                    title=None,
                    titleAlign="center",
                ),
            ),
            tooltip=[
                alt.Tooltip("category", title="Lender Group"),
                alt.Tooltip("value", title="Market Share %"),
            ],
        )
        .properties(height=300, title=title)
    )
    st.altair_chart(chart, use_container_width=True)


def _show_introduction(df: pd.DataFrame) -> None:
    top_n = 10
    total_num_loans = df["loanAmount"].count()
    total_volume = df["loanAmount"].sum()
    top_count_series = (
        df.groupby("lenderName")["loanAmount"]
        .count()
        .sort_values(ascending=False)
        .head(top_n)
    )
    top_n_lenders_by_num_loans: List[str] = top_count_series.index.tolist()

    # Calculate market share of top N lenders by volume
    top_n_lender_vol_marketshare: float = (
        df[df["lenderName"].isin(top_n_lenders_by_num_loans)]["loanAmount"].sum()
        / df["loanAmount"].sum()
        if df["loanAmount"].sum() != 0
        else 0.0
    )

    # Calculate market share of top N lenders by number of loans
    top_n_lender_num_loans_marketshare: float = (
        df[df["lenderName"].isin(top_n_lenders_by_num_loans)]["loanAmount"].count()
        / df["loanAmount"].count()
        if df["loanAmount"].count() != 0
        else 0.0
    )

    st.markdown(
        f"""
        The top {top_n} lenders by loan count accounted for 
        **{round(top_n_lender_num_loans_marketshare * 100, 1)}%**
        of all loans originated (**{total_num_loans:,}**) and
        **{round(top_n_lender_vol_marketshare * 100, 1)}%**
        of the total market volume (**{to_currency(total_volume)}**).
        """
    )

    st.write("")
    col1, col2 = st.columns(2)
    with col1:
        volume_pct: float = round(top_n_lender_num_loans_marketshare * 100, 1)
        title = "Loan Count Market Share"
        _show_donut_chart(volume_pct, title)
    with col2:
        volume_pct: float = round(top_n_lender_vol_marketshare * 100, 1)
        title = "Loan Volume Market Share"
        _show_donut_chart(volume_pct, title)

    st.markdown(f"#### Market Share of Top {top_n} Lenders")

    st.write("")
    top_n_df: pd.DataFrame = _get_df_data(df, top_n_lenders_by_num_loans)
    _show_df_introduction(top_n_df)


def _show_metrics_all_data(df: pd.DataFrame) -> None:
    total_lenders: int = df["lenderName"].nunique()
    total_num_loans: int = df["loanAmount"].count()
    avg_loan_amount: float = df["loanAmount"].mean()
    avg_num_loans: float = total_num_loans / total_lenders if total_lenders > 0 else 0

    # Calculate top count series for max loan count
    top_count_series = (
        df.groupby("lenderName")["loanAmount"].count().sort_values(ascending=False)
    )
    max_loan_count: int = top_count_series.iloc[0] if not top_count_series.empty else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Lenders", total_lenders, border=True)
    col2.metric("Average Loans Per Lender", int(avg_num_loans), border=True)
    col3.metric("Average Loan Amount", to_currency(avg_loan_amount), border=True)


def _show_metrics_selected_data(selected_data: List[Dict]) -> None:
    num_lenders: int = len(set(d.get("lenderName", "") for d in selected_data))
    if num_lenders == 0:
        avg_loans_per_lender = 0
        avg_loan_amount = 0
    else:
        avg_loans_per_lender = len(selected_data) / num_lenders
        loan_amounts = [
            float(d.get("loanAmount", 0))
            for d in selected_data
            if d.get("loanAmount") not in (None, "", "N/A")
        ]
        avg_loan_amount = sum(loan_amounts) / len(loan_amounts) if loan_amounts else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("Selected Lenders", f"{num_lenders}")
    col2.metric("Average # of Loans", f"{int(round(avg_loans_per_lender))}")
    col3.metric("Average Loan Amount", to_currency(int(avg_loan_amount)))


def _show_network_graph(selected_data: List[Dict]) -> None:
    party = "lender"
    show_relationship_network_graph(party, selected_data)

    st.info(
        f"""
        ##### :material/cognition: How to Interpret the Chart
        Yellow represents {party}s, and green represents loans.
        The size of a green dot is proportional to its loan amount.
        Arrows connect each {party} to their respective loans.
        Lenders whose portfolios contain loans of similar amounts 
        appear surrounded by uniformly sized dots.
        """
    )


def _show_slider(prepped_data: List[Dict]) -> Dict:
    if prepped_data:
        max_num_loans: int = max(
            item.get("lender_num_loans", 0) for item in prepped_data
        )
    else:
        max_num_loans = 0

    # Use a tiered filter to improve rendering speed
    if max_num_loans > 50:
        offset = int(max_num_loans * 0.25)
        slider_min = 5
        slider_max = max_num_loans
        value_min = 20
        value_max = slider_min + offset
        step = 5
    elif max_num_loans > 20:
        slider_min = 5
        slider_max = max_num_loans
        value_min = 10
        value_max = 20
        step = 1
    elif max_num_loans > 10:
        slider_min = 1
        slider_max = max_num_loans
        value_min = slider_min + 1
        value_max = max_num_loans - 1
        step = 1
    else:
        slider_min = 1
        slider_max = max_num_loans + 1
        value_min = slider_min + 1
        value_max = max_num_loans + 1
        step = 1

    user_min_num_loans, user_max_num_loans = st.slider(
        "**Adjust the slider below to select lenders by number of loans originated.**",
        min_value=slider_min,
        max_value=slider_max,
        value=(value_min, value_max),
        step=step,
    )

    slider_data: Dict = {
        "user_min_num_loans": user_min_num_loans,
        "user_max_num_loans": user_max_num_loans,
    }
    return slider_data


def render_page():
    show_st_h1("Lender Analysis")
    show_st_h2(f"Market Share - {LOCATION}", w_divider=True)

    prepped_data_file_path: str = prep_data()
    prepped_data: List[Dict] = load_json(prepped_data_file_path)

    df = pd.DataFrame(prepped_data)
    df["loanAmount"] = pd.to_numeric(df["loanAmount"], errors="coerce")

    st.write("")
    _show_introduction(df)

    st.write("")
    st.markdown("#### Loan Amount Distribution by Lender")

    st.write("")
    _show_metrics_all_data(df)

    st.write("")
    _show_bar_chart(df)

    # st.write("")
    # st.write("")
    # st.markdown("#### Loans Per Lender")

    # slider_data: Dict = _show_slider(prepped_data)

    # selected_data: List[Dict] = _get_selected_data(prepped_data, slider_data)

    # st.write("")
    # _show_df_network_graph(selected_data)

    # if not selected_data:
    #     show_st_info("no_data_selected")
    #     return

    # st.write("")
    # st.write("")
    # _show_metrics_selected_data(selected_data)

    # st.write("")
    # _show_network_graph(selected_data)

    show_default_footer()


render_page()
