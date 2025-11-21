import pandas as pd
from config import DATA_DIR


def load_degreed_learning() -> pd.DataFrame:
    """
    Load Degreed learning completions from Degreed.xlsx.

    Expected columns (based on your screenshot; adjust names if different):
        - 'Completed Date'
        - 'Employee ID'
        - 'Content ID'
        - 'Content Title'
        - 'Content Type'
        - 'Content Provider'
        - 'Completion is Verified'
        - 'Completion User Rating'
        - 'Completion Points'
        - 'Content URL'
        - 'Verified Learning Minutes'
        - 'Estimated Learning Minutes'

    Returns a DataFrame with columns:
        - completed_date
        - person_id
        - content_id
        - content_title
        - content_type
        - content_provider
        - verified_flag
        - user_rating
        - completion_points
        - content_url
        - verified_minutes
        - estimated_minutes

    Note:
        - This assumes Degreed 'Employee ID' matches your SAP person_id.
          If not, you'll need a separate mapping table.
    """
    path = DATA_DIR / "Degreed.xlsx"
    df = pd.read_excel(path, dtype=str)
    df.columns = [c.strip() for c in df.columns]

    rename_map = {
        "Completed Date": "completed_date",
        "Employee ID": "person_id",
        "Content ID": "content_id",
        "Content Title": "content_title",
        "Content Type": "content_type",
        "Content Provider": "content_provider",
        "Completion is Verified": "verified_flag",
        "Completion User Rating": "user_rating",
        "Completion Points": "completion_points",
        "Content URL": "content_url",
        "Verified Learning Minutes": "verified_minutes",
        "Estimated Learning Minutes": "estimated_minutes",
    }

    missing_cols = [c for c in rename_map.keys() if c not in df.columns]
    if missing_cols:
        raise ValueError(
            f"Degreed.xlsx is missing expected columns: {missing_cols}. "
            f"Available columns are: {list(df.columns)}"
        )

    df = df.rename(columns=rename_map)

    # Parse date
    df["completed_date"] = pd.to_datetime(
        df["completed_date"], format="%d.%m.%Y", errors="coerce"
    )

    # Strip text fields
    for col in [
        "person_id",
        "content_id",
        "content_title",
        "content_type",
        "content_provider",
        "verified_flag",
        "content_url",
    ]:
        df[col] = df[col].astype(str).str.strip()

    # Numeric conversions
    for col in ["user_rating", "completion_points", "verified_minutes", "estimated_minutes"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df[
        [
            "completed_date",
            "person_id",
            "content_id",
            "content_title",
            "content_type",
            "content_provider",
            "verified_flag",
            "user_rating",
            "completion_points",
            "content_url",
            "verified_minutes",
            "estimated_minutes",
        ]
    ]