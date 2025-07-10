from typing import Dict, List, Tuple

import pandas as pd
import streamlit as st
from streamlit_agraph import Config, Edge, Node, agraph

from constants.css import BLACK_HEX, GREEN_HEX, GREEN_LIGHT_HEX, YELLOW_HEX
from constants.dataset import END_DATE, LOCATION, START_DATE
from pipelines.prep_data_borrower_loans import prep_data
from utils.formatting import to_currency
from utils.gui import show_st_h1, show_st_h2
from utils.io import load_json

HIDE_LENDER_LABEL_THRESHOLD = 4


def _create_lender_loan_relationships(
    selected_data: List[Dict], nodes: List, edges: List
) -> Tuple[List, List]:
    lender_name_to_node_id: Dict[str, str] = dict()

    loan_amount_to_scaled = _scale_loan_amounts(
        selected_data
    )  # Compute scaling for loan amounts

    # Create nodes and edges of the network graph
    for data in selected_data:
        record_id: str = str(data.get("id"))
        lender_name: str = data.get("lenderName", "N/A")
        num_loans: int = data.get("lender_num_loans", 0)
        lender_node_title: str = f"Lender: {lender_name}"
        lender_name_value = (
            lender_name if num_loans > HIDE_LENDER_LABEL_THRESHOLD else None
        )
        if lender_name not in lender_name_to_node_id:
            lender_node_id: str = f"lender_{record_id}"
            nodes.append(
                Node(
                    id=lender_node_id,
                    title=lender_node_title,
                    label=lender_name_value,
                    color=YELLOW_HEX,
                    labelColor=BLACK_HEX,
                    size=20,
                    borderWidth=0,
                    font={"size": 24},
                )
            )
            lender_name_to_node_id[lender_name] = lender_node_id

        borrower_name: str = data.get("buyerName", "N/A")
        loan_amount: int = int(data.get("loanAmount", 0))
        loan_currency_amount: str = to_currency(loan_amount)
        scaled_size_value: float = loan_amount_to_scaled[loan_amount]

        loan_node_id: str = f"loan_{record_id}"
        loan_node_title: str = f"{loan_currency_amount} loan to {borrower_name}"
        new_loan_node: Node = Node(
            id=loan_node_id,
            title=loan_node_title,
            label=None,
            color=GREEN_HEX,
            labelColor=BLACK_HEX,
            size=int(scaled_size_value),
            borderWidth=0,
        )

        source_id = lender_name_to_node_id[lender_name]
        target_id = loan_node_id
        new_edge_node: Edge = Edge(
            source=source_id,
            target=target_id,
            color=GREEN_LIGHT_HEX,
            width=5,
        )

        nodes.append(new_loan_node)
        edges.append(new_edge_node)

    return nodes, edges


def _get_selected_data(prepped_data: List[Dict], slider_data: Dict) -> List[Dict]:
    user_min_num_loans: int = slider_data["user_min_num_loans"]
    user_max_num_loans: int = slider_data["user_max_num_loans"]

    selected_data: List[Dict] = list()
    for borrower_activity in prepped_data:
        num_loans: int = borrower_activity.get("lender_num_loans", 0)
        if num_loans >= user_min_num_loans and num_loans <= user_max_num_loans:
            selected_data.append(borrower_activity)

    return selected_data


def _show_all_data_metrics(df: pd.DataFrame) -> None:
    total_lenders: int = df["lenderName"].nunique()
    avg_loan_amount: float = df["loanAmount"].mean()
    # Calculate top count series for max loan count
    top_count_series = (
        df.groupby("lenderName")["loanAmount"].count().sort_values(ascending=False)
    )
    max_loan_count: int = top_count_series.iloc[0] if not top_count_series.empty else 0

    st.write("")
    st.write("")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Lenders", total_lenders, border=True)
    col2.metric("Highest # of Loans", max_loan_count, border=True)
    col3.metric("Average Loan Amount", to_currency(avg_loan_amount), border=True)


def _show_df(selected_data: List[Dict]) -> None:
    if selected_data:
        df = pd.DataFrame(selected_data)

        columns_to_keep = ["lenderName", "buyerName", "loanAmount"]
        df = df[columns_to_keep]
        df["loanAmount"] = pd.to_numeric(df["loanAmount"], errors="coerce")

        st.dataframe(
            df,
            use_container_width=True,
            column_config={
                "lenderName": st.column_config.TextColumn(
                    "Lender Name", width="medium"
                ),
                "buyerName": st.column_config.TextColumn(
                    "Borrower Name", width="medium"
                ),
                "loanAmount": st.column_config.NumberColumn(
                    "Loan Amount", width="small", format="dollar"
                ),
            },
        )
    else:
        st.info("No lender activity data available.")


def _scale_loan_amounts(
    selected_data: List[Dict], min_size: int = 10, max_size: int = 40
) -> Dict:
    """
    Returns a dict mapping loanAmount to scaled size between min_size and max_size.
    """
    loan_amounts: List[int] = [int(d.get("loanAmount", 0)) for d in selected_data]
    if not loan_amounts:
        return {}
    min_amt = min(loan_amounts)
    max_amt = max(loan_amounts)
    if min_amt == max_amt:
        # All values are the same, return mid value
        return {amt: (min_size + max_size) // 2 for amt in loan_amounts}

    def scale(val: int) -> float:
        return min_size + (max_size - min_size) * (val - min_amt) / (max_amt - min_amt)

    return {amt: scale(amt) for amt in loan_amounts}


def _show_network_graph(selected_data: List[Dict]) -> None:
    nodes, edges = [], []
    nodes, edges = _create_lender_loan_relationships(selected_data, nodes, edges)

    # Create the network graph
    config = Config(
        physics=True,
        directed=True,
        nodeHighlightBehavior=True,
        node={"labelProperty": "label"},
        link={"labelProperty": "label"},
    )
    agraph(nodes=nodes, edges=edges, config=config)

    st.info(
        f"""
        **How to Interpret the Graph**\n
        Yellow represents lenders, and green represents loans.
        Shape sizes are proportional to loan values.
        Arrows connect each lender to their respective loans.
        """
    )


def _show_slider_loans_per_lender(prepped_data: List[Dict]) -> Dict:
    if prepped_data:
        max_num_loans: int = max(
            item.get("lender_num_loans", 0) for item in prepped_data
        )
    else:
        max_num_loans = 0

    # Use a tiered filter to improve rendering speed
    if max_num_loans > 20:
        offset = int(max_num_loans / 10)
        slider_min = offset
        slider_max = max_num_loans
        value_min = slider_min + offset
        value_max = max_num_loans - offset
    elif max_num_loans > 10:
        slider_min = 1
        slider_max = max_num_loans
        value_min = slider_min + 1
        value_max = max_num_loans - 1
    else:
        slider_min = 1
        slider_max = max_num_loans + 1
        value_min = slider_min + 1
        value_max = max_num_loans + 1

    user_min_num_loans, user_max_num_loans = st.slider(
        "**Select lenders by adjusting the range for the number of loans per lender.**",
        min_value=slider_min,
        max_value=slider_max,
        value=(value_min, value_max),
        step=1,
    )

    slider_data: Dict = {
        "user_min_num_loans": user_min_num_loans,
        "user_max_num_loans": user_max_num_loans,
    }
    return slider_data


def _show_selected_data_metrics(selected_data: List[Dict]) -> None:
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


def _show_introduction(df: pd.DataFrame) -> None:
    top_count_series = (
        df.groupby("lenderName")["loanAmount"].count().sort_values(ascending=False)
    )
    top_avg_series = (
        df.groupby("lenderName")["loanAmount"].mean().sort_values(ascending=False)
    )
    top_count: List[str] = top_count_series.head(3).index.tolist()
    top_avg: List[str] = top_avg_series.head(3).index.tolist()

    st.markdown(
        f"""
        The following data comes from mortgages recorded between **{START_DATE}**
        and **{END_DATE}**.

        The top three lenders based on the **number of loans** are:
        1. {top_count[0] if len(top_count) > 0 else ""}
        2. {top_count[1] if len(top_count) > 1 else ""}
        3. {top_count[2] if len(top_count) > 2 else ""}

        The top three lenders based on the **average loan amount** are:
        1. {top_avg[0] if len(top_avg) > 0 else ""}
        2. {top_avg[1] if len(top_avg) > 1 else ""}
        3. {top_avg[2] if len(top_avg) > 2 else ""}
        """
    )


def render_lender_loans_page():
    show_st_h1("Lender Activity")
    show_st_h2(LOCATION, w_divider=True)

    prepped_data_file_path: str = prep_data()
    prepped_data: List[Dict] = load_json(prepped_data_file_path)

    df = pd.DataFrame(prepped_data)
    df["loanAmount"] = pd.to_numeric(df["loanAmount"], errors="coerce")

    _show_introduction(df)

    _show_all_data_metrics(df)

    st.write("")
    st.markdown("#### Loans-Per-Lender")

    slider_data: Dict = _show_slider_loans_per_lender(prepped_data)

    selected_data: List[Dict] = _get_selected_data(prepped_data, slider_data)

    st.write("")
    _show_df(selected_data)

    st.write("")
    st.write("")
    _show_selected_data_metrics(selected_data)

    st.write("")
    _show_network_graph(selected_data)


render_lender_loans_page()
