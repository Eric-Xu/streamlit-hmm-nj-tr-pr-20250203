from streamlit.navigation.page import StreamlitPage

from utils.st_app import initialize_session_state, load_css, setup_page_navigation


class MultiApp:
    def __init__(self):
        load_css()

        initialize_session_state()

    def run(self):
        pg: StreamlitPage = setup_page_navigation()
        pg.run()


app = MultiApp()
app.run()
