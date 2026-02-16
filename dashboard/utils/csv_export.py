"""CSV export utilities with injection protection."""

import pandas as pd

# Characters that can trigger formula execution in spreadsheet applications
_FORMULA_TRIGGERS = frozenset("=+\\-@")


def sanitize_csv_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Return a copy of the DataFrame with CSV injection protection applied.

    Prefixes string values starting with formula-trigger characters
    (=, +, -, @, \\) with a single quote to prevent execution in Excel/Sheets.

    Args:
        df: Source DataFrame.

    Returns:
        Sanitized copy safe for CSV export.
    """
    export_df = df.copy()
    for col in export_df.select_dtypes(include=["object"]).columns:
        export_df[col] = export_df[col].apply(
            lambda v: "'" + str(v)
            if isinstance(v, str) and v and v[0] in _FORMULA_TRIGGERS
            else v
        )
    return export_df
