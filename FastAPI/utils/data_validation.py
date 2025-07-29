import pandas as pd
from io import StringIO
from typing import List, Tuple


def validate_csv(csv_content: str, required_columns: List[str], file_name: str) -> Tuple[bool, List[str]]:
    """
    Basic CSV validation - checks structure and required columns only

    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []

    try:
        # Parse CSV
        df = pd.read_csv(StringIO(csv_content))

        # Strip whitespace from column names
        df.columns = df.columns.str.strip()

        # Check if empty
        if df.empty:
            errors.append(f"{file_name} is empty")
            return False, errors

        # Check for required columns
        missing_columns = set(required_columns) - set(df.columns)
        if missing_columns:
            errors.append(f"{file_name} missing columns: {', '.join(missing_columns)}")

        # Check for empty required columns
        for col in required_columns:
            if col in df.columns:
                empty_count = df[col].isnull().sum()
                if empty_count > 0:
                    errors.append(f"{file_name} has {empty_count} empty values in '{col}' column")

        return len(errors) == 0, errors

    except Exception as e:
        errors.append(f"Cannot read {file_name}: {str(e)}")
        return False, errors


def validate_uploaded_csvs(parts_content: str, articles_content: str) -> Tuple[bool, List[str]]:
    """
    Validate both uploaded CSV files

    Returns:
        Tuple of (both_valid, all_error_messages)
    """
    all_errors = []

    # Define required columns
    parts_columns = ['productGroupId', 'partDescription', 'quantity', 'taxable']
    articles_columns = ['productGroupId', 'articleNo', 'articleProductName', 'price',
                        'countryOfOrigin', 'supplierId', 'supplierName']

    # Validate parts CSV
    parts_valid, parts_errors = validate_csv(parts_content, parts_columns, "Parts CSV")
    all_errors.extend(parts_errors)

    # Validate articles CSV
    articles_valid, articles_errors = validate_csv(articles_content, articles_columns, "Articles CSV")
    all_errors.extend(articles_errors)

    return parts_valid and articles_valid, all_errors