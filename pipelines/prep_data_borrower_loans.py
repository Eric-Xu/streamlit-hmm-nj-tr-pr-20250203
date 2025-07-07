import logging
import os
from typing import Dict

import streamlit as st
from pandas import DataFrame

from constants.file import (
    BORROWER_ACTIVITIES_DATA_FILE,
    DATA_DIR,
    TMP_DATA_JSON,
    TMP_DIR,
)
from utils.io import load_df


def _load_data() -> DataFrame:
    borrower_activities_df: DataFrame = load_df(
        os.path.join(DATA_DIR, BORROWER_ACTIVITIES_DATA_FILE)
    )
    logging.info(f"Number of borrower activity records: {borrower_activities_df.size}")

    return borrower_activities_df


def _transform_data(borrower_activities_df: DataFrame) -> DataFrame:
    df_sorted = borrower_activities_df.sort_values(by="buyerName").copy()

    # buyer_num_loans, buyer_num_lenders, lender_num_loans, lender_num_buyers

    # Add a new column "borrower_num_loans" counting occurrences of each buyerName
    df_sorted["borrower_num_loans"] = df_sorted["buyerName"].map(
        df_sorted["buyerName"].value_counts()
    )

    # Add a new column "lender_num_loans" counting occurrences of each buyerName
    df_sorted["lender_num_loans"] = df_sorted["lenderName"].map(
        df_sorted["lenderName"].value_counts()
    )

    # Add a new column "borrower_num_lenders" counting unique lenderName for each buyerName
    lender_counts = df_sorted.groupby("buyerName")["lenderName"].nunique()
    df_sorted["borrower_num_lenders"] = df_sorted["buyerName"].map(lender_counts)

    # Add a new column "lender_num_borrowers" counting unique buyerName for each lenderName
    borrower_counts = df_sorted.groupby("lenderName")["buyerName"].nunique()
    df_sorted["lender_num_borrowers"] = df_sorted["lenderName"].map(borrower_counts)

    return df_sorted


def _save_data(prepped_data_df: DataFrame, prepped_data_file_path: str) -> None:
    logging.info(
        f"Saving transformed borrower activities data to {prepped_data_file_path}"
    )
    prepped_data_df.to_json(prepped_data_file_path, orient="records", lines=False)


@st.cache_data
def prep_data() -> str:
    borrower_activities_df: DataFrame = _load_data()

    prepped_data_df: DataFrame = _transform_data(borrower_activities_df)

    prepped_data_file_path = os.path.join(TMP_DIR, TMP_DATA_JSON)
    _save_data(prepped_data_df, prepped_data_file_path)

    return prepped_data_file_path
