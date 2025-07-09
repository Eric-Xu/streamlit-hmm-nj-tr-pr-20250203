from datetime import date, datetime
from typing import Dict, List, Tuple

import pandas as pd
import streamlit as st
from streamlit_agraph import Config, Edge, Node, agraph

from constants.css import BLACK_HEX, GREEN_HEX, GREEN_LIGHT_HEX, RED_HEX, YELLOW_HEX
from constants.dataset import END_DATE, LOCATION, START_DATE
from pipelines.prep_data_borrower_loans import prep_data
from utils.formatting import to_currency
from utils.gui import show_st_h1, show_st_h2
from utils.io import load_json

"""
TODO:
- Change repeat borrower nodes to PURPLE_HEX
- Reduce node "mass" value as number of borrowers increase.
- Set node "physics" to False for really high number of borrowers like "Kiavi".
- Add metrics for "% of repeat borrowers"
"""


def _create_borrower_loan_relationships(
    selected_data: List[Dict], nodes: List, edges: List
) -> Tuple[List, List]:
    borrower_ids_added: set = set()
    loan_ids_added: set = set()
    for data in selected_data:
        record_id: str = str(data.get("id"))
        borrower_id: str = f"borrower_{record_id}"
        borrower_name: str = data.get("buyerName", "N/A")
        borrower_node_title: str = f"Borrower: {borrower_name}"

        # Create borrower nodes based on unique borrower ids
        if borrower_id not in borrower_ids_added:
            nodes.append(
                Node(
                    id=borrower_id,
                    title=borrower_node_title,
                    label=None,
                    color=RED_HEX,
                    labelColor=BLACK_HEX,
                    size=20,
                    font={"size": 24},
                    borderWidth=0,
                    mass=0.3,
                    fixed={"x": True},
                    x=400,
                )
            )
            borrower_ids_added.add(borrower_id)

        # Create loan nodes
        loan_amount: int = int(data.get("loanAmount", 0))
        recording_date: str = data.get("recordingDate", "N/A")
        loan_currency_amount: str = to_currency(loan_amount)
        loan_id: str = f"loan_{record_id}"
        loan_node_title: str = f"{loan_currency_amount} loan to {borrower_name}"
        if loan_id not in loan_ids_added:
            nodes.append(
                Node(
                    id=loan_id,
                    title=loan_node_title,
                    label=None,
                    color=YELLOW_HEX,
                    labelColor=BLACK_HEX,
                    size=20,
                    # font={"size": 24},
                    borderWidth=0,
                )
            )
            loan_ids_added.add(loan_id)

        # Create borrower-loan relationships
        source_id = borrower_id
        target_id = loan_id
        edges.append(
            Edge(
                source=source_id,
                target=target_id,
                color=GREEN_LIGHT_HEX,
                width=5,
            )
        )
    return nodes, edges


def _create_loan_date_relationships(
    selected_data: List[Dict], nodes: List, edges: List
) -> Tuple[List, List]:
    latest_date: str | None = _get_latest_date(selected_data)
    last_12_months: List[date] = _get_last_12_months(latest_date)
    date_to_month_node_label: Dict[date, str] = _get_date_to_month_node_label(
        last_12_months
    )
    month_node_ids = {}
    # Create month nodes in chronological order
    for i, first_of_month in enumerate(sorted(last_12_months)):
        month_node_label: str | None = date_to_month_node_label.get(first_of_month)
        if not month_node_label:
            continue
        month_node_id = f"month_{i+1}"
        month_node_ids[first_of_month] = month_node_id
        label_value: str = f"  {month_node_label}  "
        x_value = 0
        y_value = i * 100
        nodes.append(
            Node(
                id=month_node_id,
                label=label_value,
                shape="circle",
                color=GREEN_HEX,
                labelColor=BLACK_HEX,
                borderWidth=0,
                physics=False,
                fixed={"x": True, "y": True},
                x=x_value,
                y=y_value,
            )
        )

    # Create loan-to-month relationships with error handling
    for data in selected_data:
        try:
            record_id: str = str(data.get("id"))
            recording_date: str = data.get("recordingDate", None)
            if not recording_date:
                continue
            first_of_month = _get_first_of_month(recording_date)
            if first_of_month not in month_node_ids:
                continue
            loan_id: str = f"loan_{record_id}"
            source_id = loan_id
            target_id = month_node_ids[first_of_month]
            if not source_id or not target_id:
                continue
            edges.append(
                Edge(
                    source=source_id,
                    target=target_id,
                    color=GREEN_LIGHT_HEX,
                    width=5,
                )
            )
        except Exception as e:
            # Optionally log the error or pass
            pass
    return nodes, edges


def _get_date_to_month_node_label(last_12_months: List[date]) -> Dict[date, str]:
    """Return a dict mapping each date to a label like "DEC '25"."""
    return {d: d.strftime("%b '%y").upper() for d in last_12_months}


def _get_first_of_month(date_str: str) -> date:
    """Convert a date string like '2025-05-10' to a date object for the first of that month (e.g., date(2025, 5, 1))."""
    dt = datetime.strptime(date_str, "%Y-%m-%d").date()
    return date(dt.year, dt.month, 1)


def _get_last_12_months(latest_date: str | None) -> List[date]:
    """Return a list of 12 date objects, each the first of the month, going back from latest_date (inclusive)."""
    months: List[date] = []
    if not latest_date:
        dt: date = date.today()
    else:
        dt: date = datetime.strptime(latest_date, "%Y-%m-%d").date()
    year, month = dt.year, dt.month
    for _ in range(12):
        months.append(date(year, month, 1))
        # Move to previous month
        if month == 1:
            year -= 1
            month = 12
        else:
            month -= 1
    return months


def _get_latest_date(selected_data: List[Dict]) -> str | None:
    """Return the latest 'recordingDate' in YYYY-MM-DD format from selected_data, or None if not found."""
    if not selected_data:
        return None
    dates: List[str] = [
        d["recordingDate"] for d in selected_data if d.get("recordingDate") is not None
    ]
    if not dates:
        return None
    return max(dates)


def _get_selected_data(prepped_data: List[Dict], lender: str) -> List[Dict]:
    return [d for d in prepped_data if d.get("lenderName", "") == lender]


def _show_df(selected_data: List[Dict]) -> None:
    if not selected_data:
        return

    df = pd.DataFrame(selected_data)

    columns_to_keep = ["recordingDate", "buyerName", "loanAmount"]
    df = df[columns_to_keep]
    df["loanAmount"] = pd.to_numeric(df["loanAmount"], errors="coerce")
    df = df.sort_values("recordingDate")

    st.dataframe(
        df,
        use_container_width=True,
        column_config={
            "recordingDate": st.column_config.TextColumn(
                "Recording Date", width="small"
            ),
            "buyerName": st.column_config.TextColumn("Borrower Name", width="medium"),
            "loanAmount": st.column_config.NumberColumn(
                "Loan Amount", width="small", format="dollar"
            ),
        },
    )


def _show_network_graph(selected_data: List[Dict]) -> None:
    if not selected_data:
        return

    nodes, edges = [], []
    nodes, edges = _create_borrower_loan_relationships(selected_data, nodes, edges)
    nodes, edges = _create_loan_date_relationships(selected_data, nodes, edges)

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
        Yellow represents lenders. 
        Green represents loans; Shape sizes are proportional to loan values. 
        Arrows connect a lender to their loans.
        """
    )


def _show_selectbox(prepped_data: List[Dict]) -> str:
    lenders = sorted(
        set(d.get("lenderName", "") for d in prepped_data if d.get("lenderName", ""))
    )
    option: str = st.selectbox(
        "Enter the lender's name.",
        lenders,
    )
    return option


def render_lender_timeline_page():
    show_st_h1("Lender Timeline")
    show_st_h2(LOCATION, w_divider=True)

    prepped_data_file_path: str = prep_data()
    prepped_data: List[Dict] = load_json(prepped_data_file_path)

    st.markdown(
        f"""
        The following data comes from mortgages recorded between **{START_DATE}**
        and **{END_DATE}**.
        """
    )

    selected_lender: str = _show_selectbox(prepped_data)

    selected_data: List[Dict] = _get_selected_data(prepped_data, selected_lender)

    _show_network_graph(selected_data)

    _show_df(selected_data)


render_lender_timeline_page()
