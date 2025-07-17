from typing import Dict, List


def get_borrower_to_last_lender(prepped_data: List[Dict]) -> Dict[str, str]:
    """
    For each borrower (buyerName), find the lender (lenderName) from their most recent loan (by recordingDate).
    Returns a dict mapping borrower name to last lender name.
    """
    borrower_to_latest: Dict[str, Dict] = {}
    for record in prepped_data:
        borrower = record.get("buyerName")
        date = record.get("recordingDate")
        if not borrower or not date:
            continue
        if (
            borrower not in borrower_to_latest
            or date > borrower_to_latest[borrower]["recordingDate"]
        ):
            borrower_to_latest[borrower] = record
    # Map borrower to their last lender
    return {
        borrower: rec.get("lenderName", "")
        for borrower, rec in borrower_to_latest.items()
    }


def get_lender_to_all_borrowers(prepped_data: List[Dict]) -> Dict[str, List[str]]:
    """
    For each lender (lenderName), collect a list of all borrowers (buyerName) they've lent to.
    Returns a dict mapping lender name to a list of borrower names.
    """
    lender_to_borrowers: Dict[str, List[str]] = {}
    for record in prepped_data:
        lender = record.get("lenderName")
        borrower = record.get("buyerName")
        if not lender or not borrower:
            continue
        if lender not in lender_to_borrowers:
            lender_to_borrowers[lender] = []
        lender_to_borrowers[lender].append(borrower)
    return lender_to_borrowers


def get_lender_to_churned_borrowers(
    lender_to_all_borrowers: Dict[str, List[str]],
    borrower_to_last_lender: Dict[str, str],
) -> Dict[str, List[str]]:
    """
    For each lender, find borrowers who have churned (last loan was to a different lender).
    Returns a dict mapping lender name to a list of unique churned borrower names.
    """
    lender_to_churned: Dict[str, List[str]] = {}
    for lender, borrowers in lender_to_all_borrowers.items():
        churned_borrowers = set()
        for borrower in borrowers:
            if borrower_to_last_lender.get(borrower) != lender:
                churned_borrowers.add(borrower)
        if churned_borrowers:
            lender_to_churned[lender] = list(churned_borrowers)
    return lender_to_churned
