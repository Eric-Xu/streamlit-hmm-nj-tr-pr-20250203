from typing import Dict, List, Tuple

import pandas as pd
import streamlit as st

from constants.css import GREEN_HEX
from constants.dataset import END_DATE, LOCATION, START_DATE
from pipelines.prep_data_borrower_loans import prep_data
from utils.gui import show_st_h1, show_st_h2
from utils.io import load_json


def _get_selected_data(
    prepped_data: List[Dict], user_min_loan_amount: int, user_max_loan_amount: int
) -> List[Dict]:
    selected_data: List[Dict] = list()
    for borrower_activity in prepped_data:
        loan_amount: int = int(borrower_activity.get("loanAmount", 0))
        if loan_amount >= user_min_loan_amount and loan_amount <= user_max_loan_amount:
            selected_data.append(borrower_activity)

    return selected_data


def _prep_borrower_loan_data(selected_data: List[Dict]) -> List[Dict]:
    if not selected_data:
        st.info("No data available for the bar chart.")
        return []

    # Extract loan amounts and create labels
    borrower_loan_data = []
    borrower_counts = {}  # Track how many times each borrower appears

    for i, activity in enumerate(selected_data):
        loan_amount = int(activity.get("loanAmount", 0))
        borrower_name = activity.get("buyerName", "N/A")

        # Count occurrences of this borrower name
        borrower_counts[borrower_name] = borrower_counts.get(borrower_name, 0) + 1

        # Create unique label - only add index if borrower appears multiple times
        if borrower_counts[borrower_name] > 1:
            unique_label = f"{borrower_name}_{borrower_counts[borrower_name]}"
        else:
            unique_label = borrower_name

        borrower_loan_data.append({"amount": loan_amount, "borrower": unique_label})

    # Sort by loan amount (highest to lowest)
    borrower_loan_data.sort(key=lambda x: x["amount"], reverse=True)

    return borrower_loan_data


def _show_bar_chart(borrower_loan_data: List[Dict]) -> None:
    """Display a bar chart of loan amounts ordered from highest to lowest."""
    amounts = [item["amount"] for item in borrower_loan_data]
    borrowers = [item["borrower"] for item in borrower_loan_data]

    st.markdown("#### Loan Amount Distribution")
    st.bar_chart(
        data=pd.DataFrame({"Loan Amount ($)": amounts, "Borrower": borrowers}),
        x="Borrower",
        y="Loan Amount ($)",
        color=GREEN_HEX,
        height=500,
        use_container_width=True,
    )


def _show_df(borrower_loan_data: List[Dict]) -> None:
    amounts: List[int] = [int(item["amount"]) for item in borrower_loan_data]
    borrowers: List[str] = [item["borrower"] for item in borrower_loan_data]
    df = pd.DataFrame({"Borrower Name": borrowers, "Loan Amount": amounts})
    st.dataframe(
        df,
        use_container_width=True,
        column_config={
            "Borrower Name": st.column_config.TextColumn(
                "Borrower Name", width="medium"
            ),
            "Loan Amount": st.column_config.NumberColumn(
                "Loan Amount", width="small", format="dollar"
            ),
        },
    )


def _show_introduction(prepped_data: List[Dict]) -> None:
    total_loans: int = len(prepped_data)
    loan_amounts = [int(item.get("loanAmount", 0)) for item in prepped_data]
    avg_loan_amount: float = sum(loan_amounts) / total_loans if total_loans > 0 else 0
    unique_borrowers: int = len(set(item.get("buyerName", "") for item in prepped_data))
    unique_lenders: int = len(set(item.get("lenderName", "") for item in prepped_data))

    st.markdown(
        f"""
        The following data comes from mortgages recorded between **{START_DATE}**
        and **{END_DATE}**.

        There are **{total_loans}** loans in total, with an average amount of **${avg_loan_amount:,.0f}**. 
        
        These loans involve **{unique_borrowers}** borrowers and **{unique_lenders}** lenders.
        """
    )


def _show_selected_data_metrics(borrower_loan_data: List[Dict]) -> None:
    amounts = [item["amount"] for item in borrower_loan_data]

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Selected Loans", len(amounts))
    with col2:
        st.metric("Average Loan", f"${sum(amounts)/len(amounts):,.0f}")
    with col3:
        st.metric("Highest Loan", f"${max(amounts):,.0f}")


def _show_slider(prepped_data: List[Dict]) -> Tuple[int, int]:
    max_loan_amount: int = max(int(item.get("loanAmount", 0)) for item in prepped_data)

    slider_default_min = int(max_loan_amount * 0.1)
    slider_default_max = int(max_loan_amount * 0.9)

    user_min_loan_amount, user_max_loan_amount = st.slider(
        "**Select loans by adjusting the minimum and maximum loan amounts.**",
        min_value=0,
        max_value=max_loan_amount,
        value=(slider_default_min, slider_default_max),
        step=10000,
    )

    return user_min_loan_amount, user_max_loan_amount


def render_loan_analysis_page():
    show_st_h1("Loan Analysis")
    show_st_h2(LOCATION, w_divider=True)

    prepped_data_file_path: str = prep_data()
    prepped_data: List[Dict] = load_json(prepped_data_file_path)

    _show_introduction(prepped_data)

    st.write("")
    st.write("")
    user_min_loan_amount, user_max_loan_amount = _show_slider(prepped_data)

    selected_data: List[Dict] = _get_selected_data(
        prepped_data, user_min_loan_amount, user_max_loan_amount
    )

    borrower_loan_data: List[Dict] = _prep_borrower_loan_data(selected_data)

    _show_bar_chart(borrower_loan_data)

    _show_selected_data_metrics(borrower_loan_data)

    st.write("")
    st.write("")

    _show_df(borrower_loan_data)


render_loan_analysis_page()
