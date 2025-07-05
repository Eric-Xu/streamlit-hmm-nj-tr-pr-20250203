import re
import uuid

import streamlit as st


def show_st_h1(text, w_divider=False) -> None:
    h1_str = f"<h1 class='st-key-sans-serif-header'>{text}</h1>"
    hr_str = "<hr class='st-key-header-divider'>"

    if w_divider:
        st.html(h1_str + hr_str)
    else:
        st.html(h1_str)


def show_st_h2(text, w_divider=False) -> None:
    h1_str = f"<h2 class='st-key-serif-header'>{text}</h2>"
    hr_str = "<hr class='st-key-header-divider'>"

    if w_divider:
        st.html(h1_str + hr_str)
    else:
        st.html(h1_str)
