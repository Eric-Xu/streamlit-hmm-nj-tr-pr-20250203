from collections import Counter, defaultdict
from datetime import date, datetime
from typing import Dict, List, Tuple

import pandas as pd
import streamlit as st
from streamlit_agraph import Config, Edge, Node, agraph

from constants.css import (
    BLACK_HEX,
    GREEN_HEX,
    GREEN_LIGHT_HEX,
    PURPLE_HEX,
    RED_HEX,
    YELLOW_HEX,
)
from constants.dataset import END_DATE, LOCATION, START_DATE
from pipelines.prep_data_borrower_loans import prep_data
from utils.formatting import to_currency
from utils.gui import show_st_h1, show_st_h2
from utils.io import load_json

# TODO refactor common code with lender_timeline_page.py


def _add_lender_num_loans(selected_data: List[Dict]) -> List[Dict]:
    """
    Adds a 'lender_selected_num_loans' key to each dict in the list,
    counting how many times each lenderName occurs in the list.
    """
    # Count occurrences of each lenderName
    lender_counts = Counter(
        d.get("lenderName") for d in selected_data if d.get("lenderName") is not None
    )

    # Add the count to each dict
    for d in selected_data:
        lender_name = d.get("lenderName")
        d["lender_selected_num_loans"] = lender_counts.get(lender_name, 0)

    return selected_data


def _count_repeat_lenders(selected_data: List[Dict]) -> int:
    """
    Returns the number of lenders who have taken out more than one loan (repeat lenders).
    """
    lender_names = [d.get("lenderName") for d in selected_data if d.get("lenderName")]
    counts = Counter(lender_names)
    repeat_lenders = [name for name, count in counts.items() if count > 1]

    return len(repeat_lenders)


def _count_unique_lenders(selected_data: List[Dict]) -> int:
    lender_names = set()
    for d in selected_data:
        lender_name = d.get("lenderName")
        if lender_name:
            lender_names.add(lender_name)
    count: int = len(lender_names)

    return count


def _create_lender_loan_relationships(
    selected_data: List[Dict], nodes: List, edges: List
) -> Tuple[List, List]:
    lender_name_to_node_id: Dict[str, str] = dict()  # Map lender name to node ID

    selected_data = _add_lender_num_loans(selected_data)
    unique_lenders: int = _count_unique_lenders(selected_data)
    mass: float = _get_scaled_mass(unique_lenders)

    for data in selected_data:
        record_id: str = str(data.get("id"))
        lender_node_id: str = f"lender_{record_id}"
        lender_name: str = data.get("lenderName", "N/A")
        lender_node_title: str = f"Lender: {lender_name}"
        lender_num_loans: int = data.get("lender_selected_num_loans", 0)

        # Assign different node style for repeat lenders.
        color: str = PURPLE_HEX if lender_num_loans > 1 else RED_HEX
        x_value: int = 0 if lender_num_loans > 1 else 50
        label: str | None = lender_name if lender_num_loans > 1 else None

        # Only create new lender nodes based on the lender name.
        if lender_name not in lender_name_to_node_id:
            nodes.append(
                Node(
                    id=lender_node_id,
                    title=lender_node_title,
                    label=label,
                    color=color,
                    labelColor=BLACK_HEX,
                    size=20,
                    borderWidth=0,
                    mass=mass,
                    fixed={"x": True},
                    x=x_value,
                )
            )
            lender_name_to_node_id[lender_name] = lender_node_id

        # Create loan nodes
        loan_amount: int = int(data.get("loanAmount", 0))
        recording_date: str = data.get("recordingDate", "N/A")
        address: str = data.get("address", "N/A")
        loan_currency_amount: str = to_currency(loan_amount)
        loan_node_id: str = f"loan_{record_id}"
        loan_node_title: str = (
            f"{loan_currency_amount} recorded on {recording_date}\nProperty: {address}"
        )
        nodes.append(
            Node(
                id=loan_node_id,
                title=loan_node_title,
                label=None,
                color=YELLOW_HEX,
                labelColor=BLACK_HEX,
                size=20,
                borderWidth=0,
            )
        )

        # Create lender-loan relationships
        source_id = lender_name_to_node_id[lender_name]
        target_id = loan_node_id
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
    unique_lenders: int = _count_unique_lenders(selected_data)
    y_scaling_factor: int = _get_y_scaling_factor(unique_lenders)

    latest_date: str | None = _get_latest_date(selected_data)
    last_12_months: List[date] = _get_last_12_months(latest_date)
    date_to_month_node_label: Dict[date, str] = _get_date_to_month_node_label(
        last_12_months
    )
    month_node_ids = {}
    # Create month nodes in reverse chronological order
    for i, first_of_month in enumerate(sorted(last_12_months, reverse=True)):
        month_node_label: str | None = date_to_month_node_label.get(first_of_month)
        if not month_node_label:
            continue
        month_node_title: str = month_node_label
        month_node_id = f"month_{i+1}"
        month_node_ids[first_of_month] = month_node_id
        label_value: str = f"  {month_node_label}  "
        x_value = 400
        y_value = i * y_scaling_factor
        nodes.append(
            Node(
                id=month_node_id,
                title=month_node_title,
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
    """
    Return the latest 'recordingDate' in YYYY-MM-DD format from
    selected_data, or None if not found.
    """
    if not selected_data:
        return None
    dates: List[str] = [
        d["recordingDate"] for d in selected_data if d.get("recordingDate") is not None
    ]
    if not dates:
        return None

    return max(dates)


def _get_scaled_mass(unique_lenders: int) -> float:
    # Use a tiered approach to calculate the mass value
    if unique_lenders > 40:
        mass = 0.1
    elif unique_lenders > 30:
        mass = 0.2
    elif unique_lenders > 20:
        mass = 0.3
    elif unique_lenders > 10:
        mass = 0.8
    else:
        mass = 1.0

    return mass


def _get_selected_data(prepped_data: List[Dict], borrower: str) -> List[Dict]:
    return [d for d in prepped_data if d.get("buyerName", "") == borrower]


def _get_top_borrowers_by_repeat_lender_pct(
    prepped_data: List[Dict], min_num_loans, top_n: int = 5
) -> list[tuple[str, float, str, int, int]]:
    """
    Returns a list of tuples:
        (borrower_name, max_lender_pct, max_lender_name, num_loans_from_max_lender, num_loans)
    for the top_n borrowers by the highest percentage of loans from a single lender.
    Only considers borrowers with more than min_num_loans.
    """
    # Group all records by borrower
    borrower_to_records = defaultdict(list)
    for d in prepped_data:
        borrower = d.get("buyerName")
        if borrower:
            borrower_to_records[borrower].append(d)

    results = []
    for borrower, records in borrower_to_records.items():
        num_loans = len(records)
        if num_loans < min_num_loans:
            continue
        lender_counts = Counter(
            d.get("lenderName") for d in records if d.get("lenderName")
        )
        if not lender_counts:
            continue
        max_lender_name, max_lender_count = lender_counts.most_common(1)[0]
        max_lender_pct = (max_lender_count / num_loans) * 100 if num_loans > 0 else 0
        results.append(
            (borrower, max_lender_pct, max_lender_name, max_lender_count, num_loans)
        )

    # Sort by highest single-lender percentage, descending
    results.sort(key=lambda x: x[1], reverse=True)
    return results[:top_n]


def _get_y_scaling_factor(unique_lenders: int) -> int:
    if unique_lenders > 100:
        y_scaling_factor = 300
    elif unique_lenders > 80:
        y_scaling_factor = 250
    elif unique_lenders > 60:
        y_scaling_factor = 200
    elif unique_lenders > 40:
        y_scaling_factor = 150
    else:
        y_scaling_factor = 100

    return y_scaling_factor


def _show_df(selected_data: List[Dict]) -> None:
    if not selected_data:
        return

    df = pd.DataFrame(selected_data)

    columns_to_keep = ["recordingDate", "lenderName", "loanAmount"]
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
            "lenderName": st.column_config.TextColumn("Lender Name", width="medium"),
            "loanAmount": st.column_config.NumberColumn(
                "Loan Amount", width="small", format="dollar"
            ),
        },
    )


def _show_introduction() -> None:
    top_n = 10
    min_num_loans = 4

    prepped_data_file_path: str = prep_data()
    prepped_data: List[Dict] = load_json(prepped_data_file_path)
    top_borrowers = _get_top_borrowers_by_repeat_lender_pct(
        prepped_data, min_num_loans, top_n
    )

    top_borrower_lines = []
    for i, (
        borrower,
        pct,
        max_lender_name,
        num_loans_from_max_lender,
        num_loans,
    ) in enumerate(top_borrowers, 1):
        pct_value: int = int(round(pct))
        top_borrower_lines.append(
            f"{borrower} (**{pct_value}%** of {num_loans} total loans)"
        )

    st.markdown(
        f"""
        View any borrower's recorded loan transactions over a 12-month period. 
        Explore their lender relationships to identify loyal borrowers who 
        consistently use the same funding source versus those who borrow from 
        different lenders each time.

        The top {top_n} borrowers (with at least {min_num_loans} loans) ranked 
        by the percentage of loans from a single lender.
        
        1. {top_borrower_lines[0] if len(top_borrower_lines) > 0 else ""}
        1. {top_borrower_lines[1] if len(top_borrower_lines) > 1 else ""}
        1. {top_borrower_lines[2] if len(top_borrower_lines) > 2 else ""}
        1. {top_borrower_lines[3] if len(top_borrower_lines) > 3 else ""}
        1. {top_borrower_lines[4] if len(top_borrower_lines) > 4 else ""}
        1. {top_borrower_lines[5] if len(top_borrower_lines) > 5 else ""}
        1. {top_borrower_lines[6] if len(top_borrower_lines) > 6 else ""}
        1. {top_borrower_lines[7] if len(top_borrower_lines) > 7 else ""}
        1. {top_borrower_lines[8] if len(top_borrower_lines) > 8 else ""}
        1. {top_borrower_lines[9] if len(top_borrower_lines) > 9 else ""}
        
        Simply type or select the borrower's name in the search field below to begin.

        This data covers loans recorded from **{START_DATE}** to **{END_DATE}**.
        """
    )


def _show_metrics_selected_data(selected_data: List[Dict]) -> None:
    num_lenders: int = len(set(d.get("lenderName", "") for d in selected_data))
    if num_lenders == 0:
        return

    repeat_lender_count: int = _count_repeat_lenders(selected_data)
    repeat_lender_pct: float = (
        (repeat_lender_count / num_lenders) * 100 if num_lenders > 0 else 0
    )

    loan_amounts = [
        float(d.get("loanAmount", 0))
        for d in selected_data
        if d.get("loanAmount") not in (None, "", "N/A")
    ]
    avg_loan_amount = sum(loan_amounts) / len(loan_amounts) if loan_amounts else 0

    col1, col2, col3 = st.columns(3)
    col1.metric(
        "Repeat Lender Count",
        f"{repeat_lender_count}/{num_lenders}",
        border=True,
    )
    col2.metric(
        "Repeat Lender Pct",
        f"{int(round(repeat_lender_pct))}%",
        border=True,
    )
    col3.metric(
        "Average Loan Amount",
        to_currency(int(avg_loan_amount)),
        border=True,
    )


def _show_network_graph(selected_data: List[Dict]) -> None:
    if not selected_data:
        return

    nodes, edges = [], []
    nodes, edges = _create_lender_loan_relationships(selected_data, nodes, edges)
    nodes, edges = _create_loan_date_relationships(selected_data, nodes, edges)

    # Create the network graph
    config = Config(
        height=1000,
        directed=True,
        nodeHighlightBehavior=True,
        node={"labelProperty": "label"},
        link={"labelProperty": "label"},
    )
    agraph(nodes=nodes, edges=edges, config=config)

    borrower_name: str = selected_data[0]["buyerName"]
    st.info(
        f"""
        ##### :material/cognition:  How to Interpret the Graph
        In this visualization, **purple** shows lenders who have provided multiple 
        loans to the borrower {borrower_name}, while **red** shows one-time lenders. 
        **Yellow** indicates individual loans, and **green** represents the twelve-month 
        period since the borrower's last recorded loan.
        **Arrows** connect each lender to their respective loans, and each loan to 
        the month in which it was recorded.
        """
    )


def _show_selectbox(prepped_data: List[Dict]) -> str:
    borrowers = sorted(
        set(d.get("buyerName", "") for d in prepped_data if d.get("buyerName", ""))
    )
    option: str = st.selectbox(
        "Enter the borrower's name.",
        borrowers,
    )

    return option


def render_borrower_timeline_page():
    show_st_h1("Borrower Timeline")
    show_st_h2(LOCATION, w_divider=True)

    prepped_data_file_path: str = prep_data()
    prepped_data: List[Dict] = load_json(prepped_data_file_path)

    _show_introduction()

    st.write("")
    st.write("")
    selected_borrower: str = _show_selectbox(prepped_data)

    selected_data: List[Dict] = _get_selected_data(prepped_data, selected_borrower)

    # st.write("")
    # st.write("")
    _show_metrics_selected_data(selected_data)

    _show_network_graph(selected_data)

    _show_df(selected_data)


render_borrower_timeline_page()
