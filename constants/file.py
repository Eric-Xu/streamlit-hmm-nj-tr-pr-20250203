from constants.dataset import LOCATION

# --- APP ASSETS ---
CSS_DIR = "css"

CSS_FILE = "styles.css"


# --- APP PAGES ---
PAGE_DIR = "views"

BORROWER_LENDERS_PAGE_FILE = "borrower_lenders_page.py"
BORROWER_LOANS_PAGE_FILE = "borrower_loans_page.py"
BORROWER_TIMELINE_PAGE_FILE = "borrower_timeline_page.py"
LENDER_APPEAL_PAGE_FILE = "lender_appeal_page.py"
LENDER_BORROWER_MIGRATION_PAGE_FILE = "lender_borrower_migration_page.py"
LENDER_CHURNED_BORROWERS_PAGE_FILE = "lender_churned_borrowers_page.py"
LENDER_MARKET_SHARE_PAGE_FILE = "lender_market_share_page.py"
LENDER_ORIGINATION_TIMELINE_PAGE_FILE = "lender_origination_timeline_page.py"
LENDER_REPEAT_BORROWERS_PAGE_FILE = "lender_repeat_borrowers_page.py"
LOAN_ANALYSIS_PAGE_FILE = "loan_analysis_page.py"
MARKET_MONOPOLY_PAGE_FILE = "market_monopoly_page.py"


# --- DATA FILES ---
DATA_DIR = "data"

DATASET_LOCATION_TO_FILE = {
    "CA, Los Angeles": "ca_la_20240701_20250630.csv",
    "DC, Washington": "va_dc_20240701_20250630.csv",
    "DE": "de_20240701_20250630.csv",
    "FL, Miami": "fl_mia_20240701_20250630.csv",
    "GA, Atlanta": "ga_atl_20240701_20250630.csv",
    "IL, Chicago": "il_chi_20240701_20250630.csv",
    "MN, Minnesota": "mn_min_20240701_20250630.csv",
    "NH, MSA-Manchester-Nashua": "nh_msa_man_nas_20240701_20250630.csv",
    "PA, Philadelphia": "pa_phl_20240701_20250630.csv",
    "RI, Providence": "ri_pvd_20240701_20250630.csv",
    "TX, Arlington": "tx_arl_20240701_20250630.csv",
    "TX, Dallas": "tx_dal_20240701_20250630.csv",
    "TX, El Paso": "tx_elp_20240701_20250630.csv",
    "WA, Seattle": "wa_sea_20240701_20250630.csv",
    "WY-MSA, Cheyenne": "wy_msa_chy_20240701_20250630.csv",
}
DATA_FILE = DATASET_LOCATION_TO_FILE[LOCATION]

# --- TEMP FILES ---
TMP_DIR = "tmp"

TMP_DATA_JSON = "tmp_data.json"
