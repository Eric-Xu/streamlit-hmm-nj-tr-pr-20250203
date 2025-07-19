from collections import Counter, defaultdict
from typing import Dict, List

import pandas as pd
import streamlit as st

from constants.dataset import END_DATE, LOCATION, START_DATE
from pipelines.prepare_loan_data import prep_data
from utils.formatting import to_currency
from utils.gui import show_st_h1, show_st_h2
from utils.io import load_json
from utils.party_to_loan_timeline import show_timeline_network_graph


def _count_repeat_borrowers(selected_data: List[Dict]) -> int:
    """
    Returns the number of borrowers who have taken out more than one loan (repeat borrowers).
    """
    borrower_names = [d.get("buyerName") for d in selected_data if d.get("buyerName")]
    counts = Counter(borrower_names)
    repeat_borrowers = [name for name, count in counts.items() if count > 1]
    return len(repeat_borrowers)


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

        *(This data covers loans recorded from **{START_DATE}** to **{END_DATE}**)*.
        """
    )


def _show_network_graph(selected_data: List[Dict]) -> None:
    if not selected_data:
        return

    show_timeline_network_graph("borrower", selected_data)

    lender_name: str = selected_data[0]["lenderName"]
    st.info(
        f"""
        ##### :material/cognition:  How to Interpret the Chart
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
        (repeat_borrower_count / num_borrowers) * 100 if num_borrowers > 0 else 0.0
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
        f"{round(repeat_borrower_pct, 1)}%",
        border=True,
    )
    col3.metric(
        "Average Loan Amount",
        to_currency(int(avg_loan_amount)),
        border=True,
    )


def render_page():
    show_st_h1("Lender Analysis")
    show_st_h2("Portfolio Timeline", w_divider=True)

    prepped_data_file_path: str = prep_data()
    prepped_data: List[Dict] = load_json(prepped_data_file_path)

    st.write("")
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


render_page()
