from typing import Dict, List, Set, Tuple

import pandas as pd
import streamlit as st
from streamlit_agraph import Config, Edge, Node, agraph

from constants.css import BLACK_HEX, BLUE_HEX, GREEN_HEX, GREEN_LIGHT_HEX
from constants.dataset import END_DATE, LOCATION, START_DATE
from pipelines.prep_data_borrower_loans import prep_data
from utils.formatting import format_loan_amount_to_currency
from utils.gui import show_st_h1, show_st_h2
from utils.io import load_json

HIDE_BORROWER_LABEL_THRESHOLD = 1


def _get_selected_data(prepped_data: List[Dict], slider_data: Dict) -> List[Dict]:
    user_min_num_loans: int = slider_data["user_min_num_loans"]
    user_max_num_loans: int = slider_data["user_max_num_loans"]

    selected_data: List[Dict] = list()
    for borrower_activity in prepped_data:
        num_loans: int = borrower_activity.get("num_loans", 0)
        if num_loans >= user_min_num_loans and num_loans <= user_max_num_loans:
            selected_data.append(borrower_activity)

    return selected_data


def _show_df_borrower_loans(selected_data: List[Dict]) -> None:
    if selected_data:
        # Convert the list of dictionaries to a pandas DataFrame for better display
        df = pd.DataFrame(selected_data)

        # Remove saleValue and isCorporate columns
        columns_to_keep = ["buyerName", "lenderName", "loanAmount"]
        df = df[columns_to_keep]

        # Format the numeric columns for better readability
        if "loanAmount" in df.columns:
            df["loanAmount"] = df["loanAmount"].apply(
                lambda x: (
                    f"${float(x):,.0f}"
                    if pd.notna(x)
                    and str(x).replace(".", "").replace("-", "").isdigit()
                    else "N/A"
                )
            )

        # Display the table with pagination
        st.dataframe(
            df,
            use_container_width=True,
            # hide_index=True,
            column_config={
                "buyerName": st.column_config.TextColumn(
                    "Borrower Name", width="medium"
                ),
                "lenderName": st.column_config.TextColumn(
                    "Lender Name", width="medium"
                ),
                "loanAmount": st.column_config.TextColumn("Loan Amount", width="small"),
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


def _show_network_graph_borrower_loans(selected_data: List[Dict]) -> None:
    nodes, edges = [], []
    borrower_index, loan_index = 1, 1
    # seen_borrowers: Set = set()
    borrower_name_to_node_id: Dict[str, str] = dict()  # Map borrower name to node ID
    loan_counts: Dict = dict()  # Track how many times each loan appears

    loan_amount_to_scaled = _scale_loan_amounts(
        selected_data
    )  # Compute scaling for loan amounts

    # Create nodes and edges of the network graph
    for borrower_activity in selected_data:
        borrower_name: str = borrower_activity.get("buyerName", "N/A")
        num_loans: int = borrower_activity.get("num_loans", 0)
        borrower_node_title: str = f"Borrower: {borrower_name}"
        borrower_name_value = (
            borrower_name if num_loans > HIDE_BORROWER_LABEL_THRESHOLD else None
        )
        if borrower_name not in borrower_name_to_node_id:
            borrower_node_id: str = f"borrower_{borrower_index}"
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
            # seen_borrowers.add(borrower_name)
            borrower_index += 1  # Increment borrower index

        lender_name: str = borrower_activity.get("lenderName", "N/A")
        loan_amount: int = int(borrower_activity.get("loanAmount", 0))
        loan_currency_amount: str = format_loan_amount_to_currency(loan_amount)
        scaled_size_value: float = loan_amount_to_scaled[loan_amount]

        # Count occurrences of this loan
        loan_instance: str = f"{borrower_name} {lender_name} {loan_amount}"
        loan_counts[loan_instance] = loan_counts.get(loan_instance, 0) + 1

        # Create unique label - only add index if loan appears multiple times
        loan_count: int = loan_counts[loan_instance]
        if loan_count > 1:
            loan_node_title: str = (
                f"{loan_currency_amount} loan by {lender_name}_{loan_count}"  # TODO is this still needed?
            )
        else:
            loan_node_title: str = f"{loan_currency_amount} loan by {lender_name}"

        loan_node_id: str = f"loan_{loan_index}"
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
        loan_index += 1  # Increment loan index

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
        **Legend:** 
        Blue represents borrowers. 
        Green represents loans; Shape sizes are proportional to loan values. 
        Arrows connect a borrower to their loans.
        """
    )


def _show_slider_loans_per_borrower(prepped_data: List[Dict]) -> Dict:
    if prepped_data:
        max_num_loans: int = max(item.get("num_loans", 0) for item in prepped_data)
    else:
        max_num_loans = 0

    # Use a tiered filter to improve rendering speed
    if max_num_loans > 40:
        slider_min = 4
        value_min = slider_min + 4
        value_max = max_num_loans - 4
    elif max_num_loans > 30:
        slider_min = 3
        value_min = slider_min + 3
        value_max = max_num_loans - 3
    elif max_num_loans > 20:
        slider_min = 2
        value_min = slider_min + 2
        value_max = max_num_loans - 2
    elif max_num_loans > 10:
        slider_min = 1
        value_min = slider_min + 1
        value_max = max_num_loans - 1
    else:
        slider_min = 0
        value_min = slider_min + 1
        value_max = max_num_loans - 1

    st.markdown("#### Loans-Per-Borrower")
    user_min_num_loans, user_max_num_loans = st.slider(
        "**Select borrowers by adjusting the range for number of loans-per-borrower.**",
        min_value=slider_min,
        max_value=max_num_loans,
        value=(value_min, value_max),
        step=1,
    )

    slider_data: Dict = {
        "user_min_num_loans": user_min_num_loans,
        "user_max_num_loans": user_max_num_loans,
    }
    return slider_data


def st_page_borrower_loans():
    show_st_h1("Borrower Activity")
    show_st_h2(LOCATION, w_divider=True)

    st.markdown(
        f"""
        The following data shows all mortgages recorded between **{START_DATE}**
        and **{END_DATE}**.
        """
    )
    st.write("")

    prepped_data_file_path: str = prep_data()
    prepped_data: List[Dict] = load_json(prepped_data_file_path)

    slider_data: Dict = _show_slider_loans_per_borrower(prepped_data)

    selected_data: List[Dict] = _get_selected_data(prepped_data, slider_data)

    st.write("")
    _show_df_borrower_loans(selected_data)

    st.write("")
    _show_network_graph_borrower_loans(selected_data)


st_page_borrower_loans()
