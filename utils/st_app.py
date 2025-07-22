import hmac
import os
from pathlib import Path

import streamlit as st
from streamlit.navigation.page import StreamlitPage

from constants.file import (
    BORROWER_LENDERS_PAGE_FILE,
    BORROWER_LOANS_PAGE_FILE,
    BORROWER_TIMELINE_PAGE_FILE,
    CSS_DIR,
    CSS_FILE,
    LENDER_APPEAL_PAGE_FILE,
    LENDER_BORROWER_MIGRATION_PAGE_FILE,
    LENDER_CHURNED_BORROWERS_PAGE_FILE,
    LENDER_MARKET_SHARE_PAGE_FILE,
    LENDER_ORIGINATION_TIMELINE_PAGE_FILE,
    LENDER_REPEAT_BORROWERS_PAGE_FILE,
    LOAN_ANALYSIS_PAGE_FILE,
    PAGE_DIR,
)


def check_password():
    def password_entered():
        if hmac.compare_digest(
            st.session_state["password"], st.secrets["login_password"]
        ):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store the password.
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 Password incorrect")
        return False
    else:
        return True


def initialize_session_state() -> None:
    st.session_state["subj_prop_address"] = "123 Main St"


def load_css() -> None:
    current_dir = Path(__file__).parent if "__file__" in locals() else Path.cwd()
    css_file_path = os.path.join(current_dir, CSS_DIR, CSS_FILE)

    with open(css_file_path) as f:
        st.markdown("<style>{}</style>".format(f.read()), unsafe_allow_html=True)


def setup_page_navigation() -> StreamlitPage:
    loan_analysis_page = st.Page(
        os.path.join(PAGE_DIR, LOAN_ANALYSIS_PAGE_FILE),
        title="Market Overview",
        icon=":material/bar_chart:",
        default=True,
    )
    borrower_loans_page = st.Page(
        os.path.join(PAGE_DIR, BORROWER_LOANS_PAGE_FILE),
        title="Borrowers & Loans",
        icon=":material/scatter_plot:",
    )
    borrower_timeline_page = st.Page(
        os.path.join(PAGE_DIR, BORROWER_TIMELINE_PAGE_FILE),
        title="Borrower Timeline",
        icon=":material/calendar_month:",
    )
    borrower_lenders_page = st.Page(
        os.path.join(PAGE_DIR, BORROWER_LENDERS_PAGE_FILE),
        title="Borrowers & Lenders",
        icon=":material/scatter_plot:",
    )
    lender_market_share_page = st.Page(
        os.path.join(PAGE_DIR, LENDER_MARKET_SHARE_PAGE_FILE),
        title="Market Share",
        icon=":material/incomplete_circle:",
    )
    lender_repeat_borrowers_page = st.Page(
        os.path.join(PAGE_DIR, LENDER_REPEAT_BORROWERS_PAGE_FILE),
        title="Repeat Borrowers",
        icon=":material/group:",
    )
    lender_churned_borrowers_page = st.Page(
        os.path.join(PAGE_DIR, LENDER_CHURNED_BORROWERS_PAGE_FILE),
        title="Churned Borrowers",
        icon=":material/person_cancel:",
    )
    lender_borrower_migration_page = st.Page(
        os.path.join(PAGE_DIR, LENDER_BORROWER_MIGRATION_PAGE_FILE),
        title="Borrower Migration",
        icon=":material/directions_walk:",
    )
    lender_appeal_page = st.Page(
        os.path.join(PAGE_DIR, LENDER_APPEAL_PAGE_FILE),
        title="Lender Appeal",
        icon=":material/favorite:",
    )
    lender_origination_timeline_page = st.Page(
        os.path.join(PAGE_DIR, LENDER_ORIGINATION_TIMELINE_PAGE_FILE),
        title="Origination Timeline",
        icon=":material/calendar_month:",
    )

    pages = {
        "Loan Analysis": [loan_analysis_page],
        "Borrower Analysis": [
            borrower_loans_page,
            borrower_timeline_page,
        ],
        "Lender Analysis": [
            lender_market_share_page,
            lender_origination_timeline_page,
            lender_repeat_borrowers_page,
            lender_churned_borrowers_page,
            lender_borrower_migration_page,
            lender_appeal_page,
        ],
        "Borrower-Lender Relationship": [
            borrower_lenders_page,
            # relationships_page,
            # relationship_timeline_page,
        ],
    }
    pg: StreamlitPage = st.navigation(pages)

    return pg
