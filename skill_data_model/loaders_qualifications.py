import pandas as pd
from config import DATA_DIR


def load_qualifications() -> pd.DataFrame:
    """
    Load qualification catalogue from ZPE_KOM_KVAL.xlsx.

    Expected columns in the Excel file:
        - 'ID kvalifikace'
        - 'Kvalifikace'
        - 'Číslo FM'

    Returns a DataFrame with columns:
        - qualification_id
        - qualification_name
        - fm_number
    """
    path = DATA_DIR / "ZPE_KOM_KVAL.xlsx"
    df = pd.read_excel(path, dtype=str)
    df.columns = [c.strip() for c in df.columns]

    df = df.rename(columns={
        "ID kvalifikace": "qualification_id",
        "Kvalifikace": "qualification_name",
        "Číslo FM": "fm_number"
    })

    df["qualification_id"] = df["qualification_id"].astype(str).str.strip()

    return df[["qualification_id", "qualification_name", "fm_number"]]


def load_person_qualification_history() -> pd.DataFrame:
    """
    Load person–qualification histories from ZHRPD_VZD_STA_016_RE_RHRHAZ00.xlsx.

    Expected columns in the Excel file:
        - 'ID P'
        - 'Počát.datum'
        - 'Koncové datum'
        - 'ID Q'
        - 'Název Q'

    Returns a DataFrame with columns:
        - person_id
        - qualification_id
        - valid_from
        - valid_to
    """
    path = DATA_DIR / "ZHRPD_VZD_STA_016_RE_RHRHAZ00.xlsx"
    df = pd.read_excel(path, dtype=str)
    df.columns = [c.strip() for c in df.columns]

    df = df.rename(columns={
        "ID P": "person_id",
        "Počát.datum": "valid_from",
        "Koncové datum": "valid_to",
        "ID Q": "qualification_id",
        "Název Q": "qualification_name_raw"
    })

    for col in ["valid_from", "valid_to"]:
        df[col] = pd.to_datetime(df[col], format="%d.%m.%Y", errors="coerce")

    df["person_id"] = df["person_id"].astype(str).str.strip()
    df["qualification_id"] = df["qualification_id"].astype(str).str.strip()

    person_qualification_history = df[[
        "person_id", "qualification_id", "valid_from", "valid_to"
    ]]

    return person_qualification_history


def load_training_events_and_participation():
    """
    Load SAP training events and participation from ZHRPD_VZD_STA_007.xlsx.

    Expected columns in the Excel file:
        - 'Typ akce'
        - 'Označení typu akce'
        - 'IDOBJ'
        - 'Datum zahájení'
        - 'Datum ukončení'
        - 'ID účastníka'

    Returns a tuple:
        (training_events, training_participation)

    training_events columns:
        - event_type_id
        - event_type_name

    training_participation columns:
        - person_id
        - event_type_id
        - event_instance_id
        - start_date
        - end_date
    """
    path = DATA_DIR / "ZHRPD_VZD_STA_007.xlsx"
    df = pd.read_excel(path, dtype=str)
    df.columns = [c.strip() for c in df.columns]

    # Unique event types (course types)
    training_events = df[["Typ akce", "Označení typu akce"]].drop_duplicates().rename(
        columns={
            "Typ akce": "event_type_id",
            "Označení typu akce": "event_type_name"
        }
    )
    training_events["event_type_id"] = training_events["event_type_id"].astype(str).str.strip()

    # Participation per session
    df["start_date"] = pd.to_datetime(df["Datum zahájení"],
                                      format="%d.%m.%Y", errors="coerce")
    df["end_date"] = pd.to_datetime(df["Datum ukončení"],
                                    format="%d.%m.%Y", errors="coerce")

    training_participation = df.rename(columns={
        "Typ akce": "event_type_id",
        "IDOBJ": "event_instance_id",
        "ID účastníka": "person_id"
    })[["person_id", "event_type_id", "event_instance_id", "start_date", "end_date"]]

    training_participation["person_id"] = training_participation["person_id"].astype(str).str.strip()
    training_participation["event_type_id"] = training_participation["event_type_id"].astype(str).str.strip()
    training_participation["event_instance_id"] = training_participation["event_instance_id"].astype(str).str.strip()

    return training_events, training_participation