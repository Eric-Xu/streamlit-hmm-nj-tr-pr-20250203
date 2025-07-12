import os

import streamlit_analytics2 as streamlit_analytics
from dotenv import load_dotenv
from streamlit.navigation.page import StreamlitPage

from utils.st_app import initialize_session_state, load_css, setup_page_navigation

load_dotenv()


class MultiApp:
    def __init__(self):
        load_css()

        initialize_session_state()

    def run(self):
        pg: StreamlitPage = setup_page_navigation()
        pg.run()


with streamlit_analytics.track(
    unsafe_password=os.getenv("STREAMLIT_ANALYTICS_PASSWORD", "test123")
):
    app = MultiApp()
    app.run()
