from typing import Dict, List, Tuple

import pandas as pd
import streamlit as st
from streamlit_agraph import Config, Edge, Node, agraph

from constants.css import BLACK_HEX, BLUE_HEX, GREEN_HEX, GREEN_LIGHT_HEX
from constants.dataset import END_DATE, LOCATION, START_DATE
from pipelines.prep_data_borrower_loans import prep_data
from utils.formatting import to_currency
from utils.gui import show_st_h1, show_st_h2
from utils.io import load_json

HIDE_LABEL_THRESHOLD_PCT = 0.4
MIN_HIDE_LABEL_THRESHOLD = 1


def _create_borrower_loan_relationships(
    selected_data: List[Dict], nodes: List, edges: List
) -> Tuple[List, List]:
    borrower_name_to_node_id: Dict[str, str] = dict()  # Map borrower name to node ID

    loan_amount_to_scaled = _scale_loan_amounts(
        selected_data
    )  # Compute scaling for loan amounts

    hide_label_threshold: int = _get_hide_label_threshold(
        selected_data
    )  # Compute dynamic threshold value

    # Create nodes and edges of the network graph
    for data in selected_data:
        record_id: str = str(data.get("id"))
        borrower_name: str = data.get("buyerName", "N/A")
        num_loans: int = data.get("borrower_num_loans", 0)
        borrower_node_title: str = f"Borrower: {borrower_name}"
        borrower_name_value = (
            borrower_name if num_loans > hide_label_threshold else None
        )
        # Only create new borrower nodes based on the borrower name.
        if borrower_name not in borrower_name_to_node_id:
            borrower_node_id: str = f"borrower_{record_id}"
            nodes.append(
                Node(
                    id=borrower_node_id,
                    title=borrower_node_title,
                    label=borrower_name_value,
                    color=BLUE_HEX,
                    labelColor=BLACK_HEX,
                    size=20,
                    borderWidth=0,
                    font={"size": 24},
                )
            )
            borrower_name_to_node_id[borrower_name] = borrower_node_id

        lender_name: str = data.get("lenderName", "N/A")
        loan_amount: int = int(data.get("loanAmount", 0))
        loan_currency_amount: str = to_currency(loan_amount)
        scaled_size_value: float = loan_amount_to_scaled[loan_amount]

        loan_node_id: str = f"loan_{record_id}"
        loan_node_title: str = f"{loan_currency_amount} loan by {lender_name}"
        new_loan_node: Node = Node(
            id=loan_node_id,
            title=loan_node_title,
            label=None,
            color=GREEN_HEX,
            labelColor=BLACK_HEX,
            size=int(scaled_size_value),
            borderWidth=0,
        )

        source_id = borrower_name_to_node_id[borrower_name]
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


def _get_hide_label_threshold(selected_data: List[Dict]) -> int:
    max_num_loans: int = max(
        [int(d.get("borrower_num_loans", 0)) for d in selected_data]
    )
    hide_label_threshold: int = int(max_num_loans * HIDE_LABEL_THRESHOLD_PCT)
    hide_label_threshold = (
        hide_label_threshold
        if hide_label_threshold > MIN_HIDE_LABEL_THRESHOLD
        else MIN_HIDE_LABEL_THRESHOLD
    )

    return hide_label_threshold


def _get_selected_data(prepped_data: List[Dict], slider_data: Dict) -> List[Dict]:
    user_min_num_loans: int = slider_data["user_min_num_loans"]
    user_max_num_loans: int = slider_data["user_max_num_loans"]

    selected_data: List[Dict] = list()
    for borrower_activity in prepped_data:
        num_loans: int = borrower_activity.get("borrower_num_loans", 0)
        if num_loans >= user_min_num_loans and num_loans <= user_max_num_loans:
            selected_data.append(borrower_activity)

    return selected_data


def _show_all_data_metrics(df: pd.DataFrame) -> None:
    total_borrowers: int = df["buyerName"].nunique()
    avg_loan_amount: float = df["loanAmount"].mean()
    max_loan_count: int = df.groupby("buyerName")["loanAmount"].count().max()

    st.write("")
    st.write("")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Borrowers", total_borrowers, border=True)
    col2.metric("Highest # of Loans", max_loan_count, border=True)
    col3.metric("Average Loan Amount", to_currency(avg_loan_amount), border=True)


def _show_df(selected_data: List[Dict]) -> None:
    if selected_data:
        df = pd.DataFrame(selected_data)

        columns_to_keep = ["buyerName", "lenderName", "loanAmount"]
        df = df[columns_to_keep]
        df["loanAmount"] = pd.to_numeric(df["loanAmount"], errors="coerce")

        st.dataframe(
            df,
            use_container_width=True,
            column_config={
                "buyerName": st.column_config.TextColumn(
                    "Borrower Name", width="medium"
                ),
                "lenderName": st.column_config.TextColumn(
                    "Lender Name", width="medium"
                ),
                "loanAmount": st.column_config.NumberColumn(
                    "Loan Amount", width="small", format="dollar"
                ),
            },
        )
    else:
        st.info("No borrower activity data available.")


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
    nodes, edges = _create_borrower_loan_relationships(selected_data, nodes, edges)

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
        Blue represents borrowers, and green represents loans. 
        Shape sizes are proportional to loan values. 
        Arrows connect each borrower to their respective loans.
        """
    )


def _show_slider_loans_per_borrower(prepped_data: List[Dict]) -> Dict:
    if prepped_data:
        max_num_loans: int = max(
            item.get("borrower_num_loans", 0) for item in prepped_data
        )
    else:
        max_num_loans = 0

    # Use a tiered filter to improve rendering speed
    if max_num_loans > 40:
        offset = int(max_num_loans / 10)
        slider_min = offset
        slider_max = max_num_loans
        value_min = offset * 2
        value_max = offset * 4
    elif max_num_loans > 10:
        offset = int(max_num_loans / 10)
        slider_min = offset
        slider_max = max_num_loans
        value_min = offset * 2
        value_max = 10
    else:
        slider_min = 1
        slider_max = max_num_loans + 1
        value_min = slider_min + 1
        value_max = max_num_loans + 1

    user_min_num_loans, user_max_num_loans = st.slider(
        "**Select borrowers by adjusting the range for the number of loans per borrower.**",
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
    num_borrowers: int = len(set(d.get("buyerName", "") for d in selected_data))
    if num_borrowers == 0:
        avg_loans_per_borrower = 0
        avg_loan_amount = 0
    else:
        avg_loans_per_borrower = len(selected_data) / num_borrowers
        loan_amounts = [
            float(d.get("loanAmount", 0))
            for d in selected_data
            if d.get("loanAmount") not in (None, "", "N/A")
        ]
        avg_loan_amount = sum(loan_amounts) / len(loan_amounts) if loan_amounts else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("Selected Borrowers", f"{num_borrowers}")
    col2.metric("Average # of Loans", f"{int(round(avg_loans_per_borrower))}")
    col3.metric("Average Loan Amount", to_currency(int(avg_loan_amount)))


def _show_introduction(df: pd.DataFrame) -> None:
    top_count: List[str] = (
        df.groupby("buyerName")["loanAmount"]
        .count()
        .sort_values(ascending=False)
        .head(3)
        .index.tolist()
    )

    top_avg: List[str] = (
        df.groupby("buyerName")["loanAmount"]
        .mean()
        .sort_values(ascending=False)
        .head(3)
        .index.tolist()
    )

    st.markdown(
        f"""
        The following data comes from mortgages recorded between **{START_DATE}**
        and **{END_DATE}**.

        The top three borrowers based on the **number of loans** are:
        1. {top_count[0] if len(top_count) > 0 else ""}
        2. {top_count[1] if len(top_count) > 1 else ""}
        3. {top_count[2] if len(top_count) > 2 else ""}

        The top three borrowers based on the **average loan amount** are:
        1. {top_avg[0] if len(top_avg) > 0 else ""}
        2. {top_avg[1] if len(top_avg) > 1 else ""}
        3. {top_avg[2] if len(top_avg) > 2 else ""}
        """
    )


def render_borrower_loans_page():
    show_st_h1("Borrower Activity")
    show_st_h2(LOCATION, w_divider=True)

    prepped_data_file_path: str = prep_data()
    prepped_data: List[Dict] = load_json(prepped_data_file_path)

    df = pd.DataFrame(prepped_data)
    df["loanAmount"] = pd.to_numeric(df["loanAmount"], errors="coerce")

    _show_introduction(df)

    _show_all_data_metrics(df)

    st.write("")
    st.markdown("#### Loans-Per-Borrower")

    slider_data: Dict = _show_slider_loans_per_borrower(prepped_data)

    selected_data: List[Dict] = _get_selected_data(prepped_data, slider_data)

    st.write("")
    _show_df(selected_data)

    st.write("")
    st.write("")
    _show_selected_data_metrics(selected_data)

    st.write("")
    _show_network_graph(selected_data)


render_borrower_loans_page()
