import pandas as pd
from io import StringIO
from typing import List, Tuple, Optional


def validate_csv(csv_content: str, required_columns: List[str], file_name: str,
                 optional_columns: Optional[List[str]] = None) -> Tuple[bool, List[str]]:
    """
    Enhanced CSV validation - checks structure, required columns, and data types

    Args:
        csv_content: Raw CSV content as string
        required_columns: List of columns that must be present
        file_name: Name for error reporting
        optional_columns: List of columns that are optional but valid

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
            errors.append(f"{file_name} missing required columns: {', '.join(sorted(missing_columns))}")

        # Check for unexpected columns (if optional_columns is provided)
        if optional_columns is not None:
            all_expected = set(required_columns + optional_columns)
            unexpected_columns = set(df.columns) - all_expected
            if unexpected_columns:
                errors.append(f"{file_name} has unexpected columns: {', '.join(sorted(unexpected_columns))}")

        # Check for empty required columns
        for col in required_columns:
            if col in df.columns:
                empty_count = df[col].isnull().sum()
                if empty_count > 0:
                    errors.append(f"{file_name} has {empty_count} empty values in required column '{col}'")

        # Basic data type validation
        if 'productId' in df.columns:
            try:
                pd.to_numeric(df['productId'], errors='raise')
            except (ValueError, TypeError):
                errors.append(f"{file_name} 'productId' column contains non-numeric values")

        if 'quantity' in df.columns:
            try:
                pd.to_numeric(df['quantity'], errors='raise')
            except (ValueError, TypeError):
                errors.append(f"{file_name} 'quantity' column contains non-numeric values")

        if 'price' in df.columns:
            try:
                pd.to_numeric(df['price'], errors='raise')
            except (ValueError, TypeError):
                errors.append(f"{file_name} 'price' column contains non-numeric values")

        if 'taxable' in df.columns:
            valid_boolean_values = {'True', 'False', 'true', 'false', '1', '0', 'TRUE', 'FALSE'}
            invalid_boolean = df[~df['taxable'].astype(str).isin(valid_boolean_values)]
            if not invalid_boolean.empty:
                errors.append(f"{file_name} 'taxable' column contains invalid boolean values")

        return len(errors) == 0, errors

    except Exception as e:
        errors.append(f"Cannot read {file_name}: {str(e)}")
        return False, errors


def validate_uploaded_csvs(parts_content: str, articles_content: str) -> Tuple[bool, List[str]]:
    """
    Validate both uploaded CSV files with the new format

    Returns:
        Tuple of (both_valid, all_error_messages)
    """
    all_errors = []

    # Updated required columns to match your CSV format
    parts_required_columns = ['productId', 'partDescription', 'quantity', 'taxable']
    parts_optional_columns = []  # Add any optional columns here

    articles_required_columns = ['productId', 'articleNo', 'price', 'countryOfOrigin',
                               'supplierId', 'supplierName']
    articles_optional_columns = ['articleProductName']  # Common optional column

    # Validate parts CSV
    parts_valid, parts_errors = validate_csv(
        parts_content,
        parts_required_columns,
        "Parts CSV",
        parts_optional_columns
    )
    all_errors.extend(parts_errors)

    # Validate articles CSV
    articles_valid, articles_errors = validate_csv(
        articles_content,
        articles_required_columns,
        "Articles CSV",
        articles_optional_columns
    )
    all_errors.extend(articles_errors)

    return parts_valid and articles_valid, all_errors