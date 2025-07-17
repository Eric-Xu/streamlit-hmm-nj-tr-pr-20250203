from datetime import datetime
from typing import Dict, List


def get_loan_amounts(prepped_data: List[Dict]) -> List[int]:
    loan_amounts: List[int] = [int(item.get("loanAmount", 0)) for item in prepped_data]

    return loan_amounts


def get_avg_loan_amount(prepped_data: List[Dict]) -> float:
    total_loans: int = len(prepped_data)
    loan_amounts: List[int] = get_loan_amounts(prepped_data)
    avg_loan_amount: float = sum(loan_amounts) / total_loans if total_loans > 0 else 0

    return avg_loan_amount


def get_monthly_num_loans(prepped_data: List[Dict]) -> List[int]:
    """
    Counts the number of loans for each month based on the 'recordingDate'
    field in the input data.
    Returns a list of 12 integers, where each element represents the number
    of loans recorded in that month (index 0 = January, 11 = December).
    Months with no loans will have a count of 0.
    """
    # Initialize counts for each month (0-11 for Jan-Dec)
    monthly_counts = [0] * 12

    for loan in prepped_data:
        recording_date = loan.get("recordingDate")
        if recording_date:
            try:
                # Parse the date string (format: YYYY-MM-DD)
                date_obj = datetime.strptime(recording_date, "%Y-%m-%d")
                # Get month (0-11, where 0=January)
                month_index = date_obj.month - 1
                monthly_counts[month_index] += 1
            except (ValueError, TypeError):
                # Skip invalid dates
                continue

    return monthly_counts


def get_total_volume(prepped_data: List[Dict]) -> int:
    loan_amounts: List[int] = get_loan_amounts(prepped_data)
    total_volume: int = sum(loan_amounts)

    return total_volume


def get_lender_to_num_loans(prepped_data: List[Dict]) -> Dict[str, int]:
    """
    Returns a dictionary mapping each lender to their number of loans.
    Assumes each item in prepped_data has a 'lenderName' field.
    """
    lender_to_num_loans: Dict[str, int] = {}
    for item in prepped_data:
        lender = item.get("lenderName")
        if lender:
            lender_to_num_loans[lender] = lender_to_num_loans.get(lender, 0) + 1

    return lender_to_num_loans


def get_lender_to_volume(prepped_data: List[Dict]) -> Dict[str, int]:
    """
    Returns a dictionary mapping each lender to their total loan amount.
    """
    lender_to_volume: Dict[str, int] = {}
    for item in prepped_data:
        lender = item.get("lenderName")
        loan_amount = int(item.get("loanAmount", 0))
        if lender:
            lender_to_volume[lender] = lender_to_volume.get(lender, 0) + loan_amount

    return lender_to_volume


def get_top_lenders_by_num_loans(prepped_data: List[Dict], top_n: int) -> List[Dict]:
    """
    Returns the records from prepped_data for the top_n lenders ordered
    by their number of loans.
    """
    lender_to_num_loans: Dict[str, int] = get_lender_to_num_loans(prepped_data)
    # Get the top_n lenders by number of loans
    top_lenders = sorted(lender_to_num_loans.items(), key=lambda x: x[1], reverse=True)[
        :top_n
    ]
    top_lender_names = set(lender for lender, _ in top_lenders)
    # Filter prepped_data for records belonging to top lenders
    top_lender_records = [
        item for item in prepped_data if item.get("lenderName") in top_lender_names
    ]

    return top_lender_records


def get_top_lenders_by_volume(prepped_data: List[Dict], top_n: int) -> List[Dict]:
    """
    Returns the records from prepped_data for the top_n lenders ordered
    by their total loan volume (loanAmount).
    """
    lender_to_volume: Dict[str, int] = get_lender_to_volume(prepped_data)
    # Get the top_n lenders by total loan volume
    top_lenders = sorted(lender_to_volume.items(), key=lambda x: x[1], reverse=True)[
        :top_n
    ]
    top_lender_names = set(lender for lender, _ in top_lenders)
    # Filter prepped_data for records belonging to top lenders
    top_lender_records = [
        item for item in prepped_data if item.get("lenderName") in top_lender_names
    ]
    return top_lender_records
