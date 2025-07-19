from collections import Counter
from typing import Dict, List, Set, Tuple


def get_borrower_fromto_lenders(prepped_data: List[Dict]) -> List[Tuple[str, str, str]]:
    """
    For each lender, find borrowers who have churned (i.e., their last loan was to a different lender),
    and create a list of (churned_borrower, from_lender, to_lender) triplets representing the migration
    of each churned borrower from their previous lender to their new lender.

    Args:
        prepped_data (List[Dict]): List of loan records, each as a dictionary.

    Returns:
        List[Tuple[str, str, str]]: List of (churned_borrower, from_lender, to_lender)
            triplets for each churned borrower.
    """
    borrower_fromto_lenders: List[Tuple[str, str, str]] = []

    borrower_to_last_lender: Dict[str, str] = get_borrower_to_last_lender(prepped_data)
    lender_to_churned_borrowers: Dict[str, Set[str]] = get_lender_to_lost_borrowers(
        prepped_data
    )

    for from_lender, churned_borrowers in lender_to_churned_borrowers.items():
        for churned_borrower in churned_borrowers:
            to_lender = borrower_to_last_lender.get(churned_borrower)
            if to_lender and to_lender != from_lender:
                borrower_fromto_lenders.append(
                    (churned_borrower, from_lender, to_lender)
                )

    return borrower_fromto_lenders


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


def get_borrower_to_lenders(prepped_data: List[Dict]) -> Dict[str, Set[str]]:
    """
    For each borrower (buyerName), return a list of unique lender names they've used.
    """
    borrower_to_lenders: Dict[str, set] = {}
    for record in prepped_data:
        borrower = record.get("buyerName")
        lender = record.get("lenderName")
        if not borrower or not lender:
            continue
        if borrower not in borrower_to_lenders:
            borrower_to_lenders[borrower] = set()
        borrower_to_lenders[borrower].add(lender)

    return borrower_to_lenders


def get_lender_to_borrowers(prepped_data: List[Dict]) -> Dict[str, Set[str]]:
    """
    For each lender (lenderName), collect a list of all borrowers (buyerName) they've lent to.
    Returns a dict mapping lender name to a list of borrower names.
    """
    lender_to_borrowers: Dict[str, Set[str]] = {}
    for record in prepped_data:
        lender = record.get("lenderName")
        borrower = record.get("buyerName")
        if not lender or not borrower:
            continue
        if lender not in lender_to_borrowers:
            lender_to_borrowers[lender] = set()
        lender_to_borrowers[lender].add(borrower)

    return lender_to_borrowers


def get_lender_to_lost_borrowers(prepped_data: List[Dict]) -> Dict[str, Set[str]]:
    """
    For each lender, find borrowers who have churned (last loan was to a different lender).
    Returns a dict mapping lender name to a list of unique churned borrower names.
    """
    lender_to_lost_borrowers: Dict[str, Set[str]] = {}

    borrower_to_last_lender: Dict[str, str] = get_borrower_to_last_lender(prepped_data)
    lender_to_all_borrowers: Dict[str, Set[str]] = get_lender_to_borrowers(prepped_data)

    for lender, borrowers in lender_to_all_borrowers.items():
        lost_borrowers = set()
        for borrower in borrowers:
            if borrower_to_last_lender.get(borrower) != lender:
                lost_borrowers.add(borrower)
        if lost_borrowers:
            lender_to_lost_borrowers[lender] = lost_borrowers

    return lender_to_lost_borrowers


def get_lender_to_gained_borrowers(prepped_data: List[Dict]) -> Dict[str, Set[str]]:
    """
    For each lender, find borrowers they have gained (borrowers whose last loan
    was with this lender, but who previously borrowed from a different lender).
    Returns a dict mapping lender name to a set of unique gained borrower names.
    """
    lender_to_gained_borrowers: Dict[str, Set[str]] = {}

    borrower_to_last_lender: Dict[str, str] = get_borrower_to_last_lender(prepped_data)
    lender_to_all_borrowers: Dict[str, Set[str]] = get_lender_to_borrowers(prepped_data)

    for borrower, last_lender in borrower_to_last_lender.items():
        # Only consider borrowers who have a last lender
        if not last_lender:
            continue
        # If the borrower has ever borrowed from a different lender
        for lender, borrowers in lender_to_all_borrowers.items():
            if lender == last_lender:
                if borrower in borrowers:
                    # Check if borrower has ever borrowed from another lender
                    borrowed_from_others = any(
                        borrower in bset and l != last_lender
                        for l, bset in lender_to_all_borrowers.items()
                    )
                    if borrowed_from_others:
                        if last_lender not in lender_to_gained_borrowers:
                            lender_to_gained_borrowers[last_lender] = set()
                        lender_to_gained_borrowers[last_lender].add(borrower)

    return lender_to_gained_borrowers


def get_fromto_lenders_w_counts(prepped_data: List[Dict]) -> List[Tuple[str, str, int]]:
    """
    Count the number of times that a borrower migrated from one lender to another
    (churned), and return a list of [from_lender, to_lender, count] records.

    Args:
        prepped_data (List[Dict]): List of loan records, each as a dictionary.

    Returns:
        List[Tuple[str, str, int]]: List of [from_lender, to_lender, count] records, where count is the number of borrowers
            who migrated from from_lender to to_lender.
    """
    borrower_fromto_lenders: List[Tuple[str, str, str]] = get_borrower_fromto_lenders(
        prepped_data
    )
    fromto_lenders: List[Tuple[str, str]] = [
        (from_lender, to_lender)
        for _, from_lender, to_lender in borrower_fromto_lenders
    ]
    fromto_counter = Counter(fromto_lenders)
    fromto_lenders_w_counts: List[Tuple[str, str, int]] = [
        (from_lender, to_lender, count)
        for (from_lender, to_lender), count in fromto_counter.items()
    ]

    return fromto_lenders_w_counts
