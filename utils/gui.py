import streamlit as st

from constants.dataset import END_DATE, LOCATION, START_DATE


def show_st_h1(text, w_divider=False) -> None:
    h1_str = f"<h1 class='st-key-sans-serif-header'>{text}</h1>"
    divider_str = "<hr class='st-key-header-divider'>"

    if w_divider:
        st.html(h1_str + divider_str)
    else:
        st.html(h1_str)


def show_st_h2(text, w_divider=False) -> None:
    h1_str = f"<h2 class='st-key-serif-header'>{text}</h2>"
    divider_str = "<hr class='st-key-header-divider'>"

    if w_divider:
        st.html(h1_str + divider_str)
    else:
        st.html(h1_str)


def show_default_footer() -> None:
    footer_text = f"""
    The data on this page represents loans with the following properties: (a) Location: {LOCATION} (b) Recording Date: {START_DATE} to {END_DATE}.
    """
    show_st_footer_p(footer_text, w_divider=True)


def show_st_footer_p(text, w_divider=False) -> None:
    text_w_brs: str = text.replace("\n", "<br>")
    p_str = f"<p class='st-key-footer'>{text_w_brs}</p>"
    divider_str = "<hr class='st-key-footer-divider'>"

    if w_divider:
        st.html(divider_str + p_str)
    else:
        st.html(p_str)
