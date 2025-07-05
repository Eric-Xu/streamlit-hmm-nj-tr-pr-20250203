import os
from pathlib import Path

import streamlit as st
from streamlit.navigation.page import StreamlitPage

from constants.dataset import LOCATION
from constants.file import (
    BORROWER_TO_LOANS_PAGE_FILE,
    CSS_DIR,
    CSS_FILE,
    LOAN_ANALYSIS_PAGE_FILE,
    PAGE_DIR,
)


def initialize_session_state() -> None:
    st.session_state["subj_prop_address"] = "123 Main St"


def load_css() -> None:
    current_dir = Path(__file__).parent if "__file__" in locals() else Path.cwd()
    css_file_path = os.path.join(current_dir, CSS_DIR, CSS_FILE)

    with open(css_file_path) as f:
        st.markdown("<style>{}</style>".format(f.read()), unsafe_allow_html=True)


def setup_page_navigation() -> StreamlitPage:
    borrower_activity_page = st.Page(
        os.path.join(PAGE_DIR, BORROWER_TO_LOANS_PAGE_FILE),
        title=LOCATION,
        icon=":material/map:",
        default=True,
    )
    loan_analysis_page = st.Page(
        os.path.join(PAGE_DIR, LOAN_ANALYSIS_PAGE_FILE),
        title="Loan Amount",
        icon=":material/bar_chart:",
    )

    pages = {
        "Borrower Activity": [borrower_activity_page],
        "Loan Analysis": [loan_analysis_page],
    }
    pg: StreamlitPage = st.navigation(pages)

    return pg
