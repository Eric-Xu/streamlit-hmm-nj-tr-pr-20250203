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


def _count_repeat_borrowers(selected_data: List[Dict]) -> int:
    """
    Returns the number of borrowers who have taken out more than one loan (repeat borrowers).
    """
    borrower_names = [d.get("buyerName") for d in selected_data if d.get("buyerName")]
    counts = Counter(borrower_names)
    repeat_borrowers = [name for name, count in counts.items() if count > 1]
    return len(repeat_borrowers)


def _count_unique_borrowers(selected_data: List[Dict]) -> int:
    borrower_names = set()
    for d in selected_data:
        borrower_name = d.get("buyerName")
        if borrower_name:
            borrower_names.add(borrower_name)
    count: int = len(borrower_names)

    return count


def _create_borrower_loan_relationships(
    selected_data: List[Dict], nodes: List, edges: List
) -> Tuple[List, List]:
    borrower_name_to_node_id: Dict[str, str] = dict()  # Map borrower name to node ID

    selected_data = _add_borrower_num_loans(selected_data)
    unique_borrowers: int = _count_unique_borrowers(selected_data)
    mass: float = _get_scaled_mass(unique_borrowers)

    for data in selected_data:
        record_id: str = str(data.get("id"))
        borrower_node_id: str = f"borrower_{record_id}"
        borrower_name: str = data.get("buyerName", "N/A")
        borrower_node_title: str = f"Borrower: {borrower_name}"
        borrower_num_loans: int = data.get("borrower_num_loans", 0)

        # Assign different node style for repeat borrowers.
        color: str = PURPLE_HEX if borrower_num_loans > 1 else RED_HEX
        x_value: int = 0 if borrower_num_loans > 1 else 50
        label: str | None = borrower_name if borrower_num_loans > 1 else None

        # Only create new borrower nodes based on the borrower name.
        if borrower_name not in borrower_name_to_node_id:
            nodes.append(
                Node(
                    id=borrower_node_id,
                    title=borrower_node_title,
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
            borrower_name_to_node_id[borrower_name] = borrower_node_id

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

        # Create borrower-loan relationships
        source_id = borrower_name_to_node_id[borrower_name]
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
    unique_borrowers: int = _count_unique_borrowers(selected_data)
    y_scaling_factor: int = _get_y_scaling_factor(unique_borrowers)

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


def _get_scaled_mass(unique_borrowers: int) -> float:
    # Use a tiered approach to calculate the mass value
    if unique_borrowers > 40:
        mass = 0.1
    elif unique_borrowers > 30:
        mass = 0.2
    elif unique_borrowers > 20:
        mass = 0.3
    elif unique_borrowers > 10:
        mass = 0.8
    else:
        mass = 1.0

    return mass


def _add_borrower_num_loans(selected_data: List[Dict]) -> List[Dict]:
    """
    Adds a 'borrower_num_loans' key to each dict in the list,
    counting how many times each buyerName occurs in the list.
    """
    # Count occurrences of each buyerName
    buyer_counts = Counter(
        d.get("buyerName") for d in selected_data if d.get("buyerName") is not None
    )

    # Add the count to each dict
    for d in selected_data:
        buyer_name = d.get("buyerName")
        d["borrower_num_loans"] = buyer_counts.get(buyer_name, 0)
    return selected_data


def _get_selected_data(prepped_data: List[Dict], lender: str) -> List[Dict]:
    return [d for d in prepped_data if d.get("lenderName", "") == lender]


def _get_y_scaling_factor(unique_borrowers: int) -> int:
    if unique_borrowers > 100:
        y_scaling_factor = 300
    elif unique_borrowers > 80:
        y_scaling_factor = 250
    elif unique_borrowers > 60:
        y_scaling_factor = 200
    elif unique_borrowers > 40:
        y_scaling_factor = 150
    else:
        y_scaling_factor = 100

    return y_scaling_factor


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


def _get_top_lenders_by_repeat_borrower_pct(
    prepped_data: List[Dict], min_num_loans, top_n: int = 5
) -> list[tuple[str, float, int, int, int]]:
    """
    Returns a list of tuples:
        (lender_name, repeat_borrower_pct, repeat_borrower_count, unique_borrower_count, num_loans)
    for the top_n lenders by repeat borrower percentage.
    Only considers lenders with more than min_num_loans.
    """
    # Group all records by lender
    lender_to_records = defaultdict(list)
    for d in prepped_data:
        lender = d.get("lenderName")
        if lender:
            lender_to_records[lender].append(d)

    results = []
    for lender, records in lender_to_records.items():
        borrower_counts = Counter(
            d.get("buyerName") for d in records if d.get("buyerName")
        )
        num_unique = len(borrower_counts)
        num_loans = len(records)
        if num_unique == 0 or num_loans <= min_num_loans:
            continue
        # Count repeat borrowers
        repeat_borrowers = [
            name for name, count in borrower_counts.items() if count > 1
        ]
        num_repeat = len(repeat_borrowers)
        pct = (num_repeat / num_unique) * 100 if num_unique > 0 else 0
        results.append((lender, pct, num_repeat, num_unique, num_loans))

    # Sort by repeat borrower percentage, descending
    results.sort(key=lambda x: x[1], reverse=True)
    return results[:top_n]


def _show_introduction() -> None:
    top_n = 5
    min_num_loans = 10

    prepped_data_file_path: str = prep_data()
    prepped_data: List[Dict] = load_json(prepped_data_file_path)
    top_lenders = _get_top_lenders_by_repeat_borrower_pct(
        prepped_data, min_num_loans, top_n
    )

    top_lender_lines = []
    for i, (lender, pct, num_repeat, num_unique, num_loans) in enumerate(
        top_lenders, 1
    ):
        top_lender_lines.append(f"{lender} ({int(round(pct))}%, {num_loans} loans)")

    st.markdown(
        f"""
        View any lender's origination activity over a 12-month period. Explore 
        their most active month or compare the number of one-time borrowers to 
        repeat borrowers.

        The top {top_n} lenders (with at least {min_num_loans} loans) ranked 
        by the **percentage of repeat borrowers** are:
        1. {top_lender_lines[0] if len(top_lender_lines) > 0 else ""}
        2. {top_lender_lines[1] if len(top_lender_lines) > 1 else ""}
        3. {top_lender_lines[2] if len(top_lender_lines) > 2 else ""}
        4. {top_lender_lines[3] if len(top_lender_lines) > 3 else ""}
        5. {top_lender_lines[4] if len(top_lender_lines) > 4 else ""}
        
        Simply type or select the lender's name in the search field below to begin.

        This data covers loans recorded from **{START_DATE}** to **{END_DATE}**.
        """
    )


def _show_network_graph(selected_data: List[Dict]) -> None:
    if not selected_data:
        return

    nodes, edges = [], []
    nodes, edges = _create_borrower_loan_relationships(selected_data, nodes, edges)
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

    lender_name: str = selected_data[0]["lenderName"]
    st.info(
        f"""
        ##### :material/cognition:  How to Interpret the Graph
        In this visualization, **purple** shows borrowers who have taken out multiple 
        loans from the lender {lender_name}, while **red** shows one-time borrowers. 
        **Yellow** indicates individual loans, and **green** represents the twelve-month 
        period since the lender's last recorded loan.
        **Arrows** connect each borrower to their respective loans, and each loan to 
        the month in which it was recorded.
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


def _show_metrics_selected_data(selected_data: List[Dict]) -> None:
    num_borrowers: int = len(set(d.get("buyerName", "") for d in selected_data))
    if num_borrowers == 0:
        return

    repeat_borrower_count: int = _count_repeat_borrowers(selected_data)
    repeat_borrower_pct: float = (
        (repeat_borrower_count / num_borrowers) * 100 if num_borrowers > 0 else 0
    )

    loan_amounts = [
        float(d.get("loanAmount", 0))
        for d in selected_data
        if d.get("loanAmount") not in (None, "", "N/A")
    ]
    avg_loan_amount = sum(loan_amounts) / len(loan_amounts) if loan_amounts else 0

    col1, col2, col3 = st.columns(3)
    col1.metric(
        "Repeat Borrower Count",
        f"{repeat_borrower_count}/{num_borrowers}",
        border=True,
    )
    col2.metric(
        "Repeat Borrower Pct",
        f"{int(round(repeat_borrower_pct))}%",
        border=True,
    )
    col3.metric(
        "Average Loan Amount",
        to_currency(int(avg_loan_amount)),
        border=True,
    )


def render_lender_timeline_page():
    show_st_h1("Lender Timeline")
    show_st_h2(LOCATION, w_divider=True)

    prepped_data_file_path: str = prep_data()
    prepped_data: List[Dict] = load_json(prepped_data_file_path)

    _show_introduction()

    st.write("")
    st.write("")
    selected_lender: str = _show_selectbox(prepped_data)

    selected_data: List[Dict] = _get_selected_data(prepped_data, selected_lender)

    st.write("")
    st.write("")
    _show_metrics_selected_data(selected_data)

    _show_network_graph(selected_data)

    _show_df(selected_data)


render_lender_timeline_page()
