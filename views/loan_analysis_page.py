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


def _show_loan_amount_bar_chart(prepped_data: List[Dict]) -> None:
    """Display a bar chart of loan amounts ordered from highest to lowest."""
    if not prepped_data:
        st.info("No data available for the bar chart.")
        return

    # Extract loan amounts and create labels
    loan_data = []
    for i, activity in enumerate(prepped_data):
        loan_amount = int(activity.get("loanAmount", 0))
        borrower_name = activity.get("buyerName", "N/A")
        loan_data.append({"amount": loan_amount, "borrower": borrower_name, "index": i})

    # Sort by loan amount (highest to lowest)
    loan_data.sort(key=lambda x: x["amount"], reverse=True)

    # Prepare data for the chart
    amounts = [item["amount"] for item in loan_data]
    borrowers = [item["borrower"] for item in loan_data]

    # Create the bar chart
    st.markdown("#### Loan Amount Distribution")
    st.bar_chart(
        data=pd.DataFrame({"Loan Amount ($)": amounts, "Borrower": borrowers}),
        x="Borrower",
        y="Loan Amount ($)",
        color=GREEN_HEX,
        height=500,
        use_container_width=True,
    )

    # Show summary statistics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Loans", len(amounts))
    with col2:
        st.metric("Average Loan", f"${sum(amounts)/len(amounts):,.0f}")
    with col3:
        st.metric("Highest Loan", f"${max(amounts):,.0f}")


def _show_slider_loan_amount(prepped_data: List[Dict]) -> Tuple[int, int]:
    max_loan_amount: int = max(int(item.get("loanAmount", 0)) for item in prepped_data)

    slider_default_min = int(max_loan_amount * 0.1)
    slider_default_max = int(max_loan_amount * 0.9)

    user_min_loan_amount, user_max_loan_amount = st.slider(
        "**Select borrowers by adjusting the minimum and maximum loan amounts.**",
        min_value=0,
        max_value=max_loan_amount,
        value=(slider_default_min, slider_default_max),
    )

    return user_min_loan_amount, user_max_loan_amount


def st_page_loan_amount():
    show_st_h1("Loan Analysis")
    show_st_h2(LOCATION, w_divider=True)

    st.markdown(
        f"""
        The following data shows all mortgages recorded between **{START_DATE}**
        and **{END_DATE}**.
        """
    )
    st.write("")
    st.write("")

    prepped_data_file_path: str = prep_data()
    prepped_data: List[Dict] = load_json(prepped_data_file_path)

    user_min_loan_amount, user_max_loan_amount = _show_slider_loan_amount(prepped_data)

    selected_data: List[Dict] = _get_selected_data(
        prepped_data, user_min_loan_amount, user_max_loan_amount
    )

    _show_loan_amount_bar_chart(selected_data)


st_page_loan_amount()
