# LOCATION = "CA, Los Angeles"
# LOCATION = "DC, Washington"
LOCATION = "DE"
# LOCATION = "FL, Miami"
# LOCATION = "GA, Atlanta"
# LOCATION = "IL, Chicago"
# LOCATION = "MN, Minnesota"
# LOCATION = "NH, MSA-Manchester-Nashua"
# LOCATION = "PA, Philadelphia"
# LOCATION = "RI, Providence"
# LOCATION = "TX, Arlington"
# LOCATION = "TX, Dallas"
# LOCATION = "TX, El Paso"
# LOCATION = "WA, Seattle"
# LOCATION = "WY-MSA, Cheyenne"

PROPERTY_TYPES = [
    "Single Family Residential",
    "Condo",
    "Townhouse",
    "Duplex",
    "Triplex",
    "Fourplex",
]

START_DATE = "2024-07-01"
END_DATE = "2025-06-30"

PARTY_TO_COUNTERPARTY = {"borrower": "lender", "lender": "borrower"}
PARTY_TO_DATASET_KEY = {"borrower": "buyerName", "lender": "lenderName"}
