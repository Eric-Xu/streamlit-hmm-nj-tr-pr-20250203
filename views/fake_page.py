import os
from typing import Dict

import streamlit as st
from streamlit_agraph import Config, Edge, Node, agraph

from constants.file import TMP_DATA_JSON, TMP_DIR
from utils.gui import show_st_h1, show_st_h2


def st_page_b2loans():

    show_st_h1("Fake Page")
    show_st_h2("Nearby Flipped Properties", w_divider=True)

    st.markdown(
        f"""
        The following map shows flipped properties from the same ZIP
        code as the subject property located at:

        *{st.session_state.subj_prop_address}*

        Use the map settings below to select nearby comps.
        """
    )

    nodes = [
        Node(
            id="Spiderman",
            label=None,
            color="#FF0000",
            labelColor="#FFFFFF",
            size=16,
        ),
        Node(
            id="Captain_Marvel",
            label="Captain Marvel",
            color="#0000FF",
            labelColor="#FFFFFF",
            size=5,
        ),
    ]

    edges = [Edge(source="Captain_Marvel", target="Spiderman")]

    config = Config(
        width=500,
        height=400,
        physics=True,
        directed=True,
        nodeHighlightBehavior=True,
        node={"labelProperty": "label"},
        link={"labelProperty": "label"},
    )

    agraph(nodes=nodes, edges=edges, config=config)


st_page_b2loans()
