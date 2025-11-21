import pandas as pd
from config import DATA_DIR


def load_skill_mapping() -> pd.DataFrame:
    """
    Load mapping between internal courses and skills from Skill_mapping.xlsx.

    Actual columns (from your file):
        - 'ID Kurzu'          (course ID)
        - 'Zkratka D'         (course code / abbreviation)
        - 'Název D'           (course name)
        - 'Téma'              (theme)
        - 'Oddělení'          (department)
        - 'Kontakní osoba'    (contact person)
        - 'Počát.datum'       (valid from)
        - 'Koncové datum'     (valid to)
        - 'Kompetence / Skill' (skill name)
        - 'Kategorie'         (category)

    We map these to a unified schema:

        - course_id
        - course_code
        - course_name
        - theme
        - department
        - contact_person
        - valid_from
        - valid_to
        - skill_name
        - category
    """
    path = DATA_DIR / "Skill_mapping.xlsx"
    df = pd.read_excel(path, dtype=str)
    df.columns = [c.strip() for c in df.columns]

    rename_map = {
        "ID Kurzu": "course_id",
        "Zkratka D": "course_code",
        "Název D": "course_name",
        "Téma": "theme",
        "Oddělení": "department",
        "Kontakní osoba": "contact_person",
        "Počát.datum": "valid_from",
        "Koncové datum": "valid_to",
        "Kompetence / Skill": "skill_name",
        "Kategorie": "category",
    }

    missing_cols = [c for c in rename_map.keys() if c not in df.columns]
    if missing_cols:
        raise ValueError(
            f"Skill_mapping.xlsx is missing expected columns: {missing_cols}. "
            f"Available columns are: {list(df.columns)}"
        )

    df = df.rename(columns=rename_map)

    # Strip text fields
    for col in [
        "course_id",
        "course_code",
        "course_name",
        "theme",
        "department",
        "contact_person",
        "skill_name",
        "category",
    ]:
        df[col] = df[col].astype(str).str.strip()

    # Parse dates
    for col in ["valid_from", "valid_to"]:
        df[col] = pd.to_datetime(df[col], format="%d.%m.%Y", errors="coerce")

    return df[
        [
            "course_id",
            "course_code",
            "course_name",
            "theme",
            "department",
            "contact_person",
            "valid_from",
            "valid_to",
            "skill_name",
            "category",
        ]
    ]


def load_programs_se() -> pd.DataFrame:
    """
    Load program / curriculum definitions from ERP_SK1.Start_month - SE.xlsx.

    Because we only saw a screenshot, this function makes an educated guess
    about the columns. You should open the file once and adjust the header
    handling and rename_map below to match the real column names.

    Screenshot sample:
        10000488 10000094 SE/B6  Mechanika a ...  Mechanics and Logistics
        10000489 10000094 SE/B5  Elektro a IT    Electrical and IT
        ...

    Two likely cases:
        A) The file has NO header row (only data):
            - We read with header=None and assign names manually.
        B) The file HAS a header row:
            - Replace header=None with header=0 and adjust rename_map.

    Current implementation assumes NO header and 5 columns:
        0: program_id
        1: parent_program_id (or some grouping ID)
        2: program_code (e.g. 'SE/B6')
        3: program_name_cs
        4: program_name_en_de

    Returns a DataFrame with columns:
        - program_id
        - parent_program_id
        - program_code
        - program_name_cs
        - program_name_intl
    """
    path = DATA_DIR / "ERP_SK1.Start_month - SE.xlsx"

    # If your file DOES have headers, change header=None to header=0
    # and adjust the rename_map below to match.
    df = pd.read_excel(path, header=None, dtype=str)

    # Ensure at least 5 columns exist
    if df.shape[1] < 5:
        raise ValueError(
            f"ERP_SK1.Start_month - SE.xlsx has {df.shape[1]} columns; "
            f"this loader expects at least 5. Please open the file and "
            f"adjust load_programs_se() accordingly."
        )

    df = df.rename(
        columns={
            0: "program_id",
            1: "parent_program_id",
            2: "program_code",
            3: "program_name_cs",
            4: "program_name_intl",  # EN/DE combined or international
        }
    )

    # Strip whitespace
    for col in ["program_id", "parent_program_id", "program_code",
                "program_name_cs", "program_name_intl"]:
        df[col] = df[col].astype(str).str.strip()

    programs = df[
        [
            "program_id",
            "parent_program_id",
            "program_code",
            "program_name_cs",
            "program_name_intl",
        ]
    ]

    return programs


def build_skills_programs_tables():
    """
    Convenience function to load both:
        - skill_mapping
        - programs (SE)

    Returns a dict:
        {
            'skill_mapping': <DataFrame>,
            'programs': <DataFrame>
        }
    """
    skill_mapping = load_skill_mapping()
    programs = load_programs_se()

    return {
        "skill_mapping": skill_mapping,
        "programs": programs,
    }