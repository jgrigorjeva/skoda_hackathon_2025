import pandas as pd
from pathlib import Path
from io import StringIO
from config import DATA_DIR

# Encoding for SAP TXT exports
SAP_ENCODING = "cp1250"  # change to "iso-8859-2" if characters look wrong


def _read_text_without_nuls(path: Path) -> StringIO:
    """
    Read a text file, remove any NUL bytes, and return a StringIO buffer.
    This lets pandas with engine='c' parse lines that originally contained NULs.
    """
    with open(path, "r", encoding=SAP_ENCODING, errors="replace") as f:
        text = f.read()
    text = text.replace("\x00", "")
    return StringIO(text)


def _find_header_row(path: Path, header_keywords=("VP", "ID obj.")):
    """
    Find the index of the header row in an RHRHAZ00 text export
    by searching for a line containing given keywords.
    """
    with open(path, "r", encoding=SAP_ENCODING, errors="replace") as f:
        lines = f.readlines()

    for i, line in enumerate(lines):
        if all(k in line for k in header_keywords):
            return i
    raise ValueError(f"Header row not found in {path}")


def load_rhrhaz00_ps(filename: str) -> pd.DataFrame:
    """
    Load Person–Position relationships (P_S file).
    Returns: person_position_history DataFrame:
      columns: person_id, position_id, valid_from, valid_to
    """
    path = DATA_DIR / filename
    header_idx = _find_header_row(path)

    buffer = _read_text_without_nuls(path)

    df = pd.read_csv(
        buffer,
        sep="\t",
        header=0,
        skiprows=header_idx,
        dtype=str,
        engine="c",
    )
    df.columns = [c.strip() for c in df.columns]

    # Filter for object type P
    df = df[df["TO"].str.strip() == "P"].copy()

    df["person_id"] = df["ID obj."].str.strip()
    df["position_id"] = df["VarPole"].str.extract(r"S\s*(\d+)", expand=False)

    for col in ["Začátek", "Konec"]:
        df[col] = pd.to_datetime(df[col].str.strip(), format="%d.%m.%Y", errors="coerce")

    person_position_history = df[["person_id", "position_id", "Začátek", "Konec"]].rename(
        columns={"Začátek": "valid_from", "Konec": "valid_to"}
    )
    person_position_history = person_position_history.dropna(subset=["position_id"])

    return person_position_history


def load_rhrhaz00_st(filename: str) -> pd.DataFrame:
    """
    Load Position–Task relationships (S_T file).
    Returns: position_tasks DataFrame:
      columns: position_id, task_id, valid_from, valid_to
    """
    path = DATA_DIR / filename
    buffer = _read_text_without_nuls(path)

    df = pd.read_csv(
        buffer,
        sep="\t",
        header=0,
        dtype=str,
        engine="c",
    )
    df.columns = [c.strip() for c in df.columns]

    df = df[df["TO"].str.strip() == "S"].copy()

    df["position_id"] = df["ID obj."].str.strip()
    df["task_id"] = df["VarPole"].str.extract(r"T\s*(\d+)", expand=False)

    for col in ["Začátek", "Konec"]:
        df[col] = pd.to_datetime(df[col].str.strip(), format="%d.%m.%Y", errors="coerce")

    position_tasks = df[["position_id", "task_id", "Začátek", "Konec"]].rename(
        columns={"Začátek": "valid_from", "Konec": "valid_to"}
    )
    position_tasks = position_tasks.dropna(subset=["task_id"])

    return position_tasks


def load_rhrhaz00_t_z(filename: str, z_type: str) -> pd.DataFrame:
    """
    Load Task–ZP/ZS/ZX relationships (T_ZP, T_ZS, T_ZX files).

    These files have a header row preceded by several "Dynamische Listenausgabe"
    lines. We first find the header row, then read from there.

    Returns: DataFrame with columns: task_id, z_id, z_type
    """
    path = DATA_DIR / filename
    header_idx = _find_header_row(path)
    buffer = _read_text_without_nuls(path)

    df = pd.read_csv(
        buffer,
        sep="\t",
        header=0,
        skiprows=header_idx,
        dtype=str,
        engine="c",
    )
    df.columns = [c.strip() for c in df.columns]

    # Keep only T as "from" object type
    df = df[df["TO"].str.strip() == "T"].copy()
    df["task_id"] = df["ID obj."].str.strip()

    pattern = rf"{z_type}\s*(\d+)"
    df["z_id"] = df["VarPole"].str.extract(pattern, expand=False)

    links = df[["task_id", "z_id"]].dropna(subset=["z_id"]).copy()
    links["z_type"] = z_type

    return links


def load_zhrpd_descr_zp(filename: str, lang_code: str) -> pd.DataFrame:
    """
    Load ZP descriptions from ZHRPD_DESCR_EXPORT_* (CS/DE/EN) TXT files.

    These are tab-separated text exports, not Excel.

    Returns: DataFrame with columns: z_type, z_id, lang, text
    """
    path = DATA_DIR / filename

    # The file has some header lines ("Dynamische Listenausgabe", etc.)
    # and then a header row containing "Var.plánu", "Typ obj.", etc.
    # We'll find the header row first.
    header_idx = None
    with open(path, "r", encoding=SAP_ENCODING, errors="replace") as f:
        lines = f.readlines()
        for i, line in enumerate(lines):
            if "Var.plánu" in line and "Typ obj." in line:
                header_idx = i
                break

    if header_idx is None:
        raise ValueError(f"Header row not found in {path}")

    # Remove NULs and read with pandas
    from io import StringIO
    text = "".join(lines)
    text = text.replace("\x00", "")
    buffer = StringIO(text)

    df = pd.read_csv(
        buffer,
        sep="\t",
        header=0,
        skiprows=header_idx,
        dtype=str,
        engine="c",
    )
    df.columns = [c.strip() for c in df.columns]

    # Filter for ZP object type
    df = df[df["Typ obj."].str.strip() == "ZP"].copy()

    df["z_type"] = "ZP"
    df["z_id"] = df["ID objektu"].str.strip()
    df["lang"] = lang_code
    df["text"] = df["Řetězec"].astype(str).str.strip()

    return df[["z_type", "z_id", "lang", "text"]]


def load_rhrhaz00_z_master(filename: str, z_type: str) -> pd.DataFrame:
    """
    Load ZS or ZX descriptions from RHRHAZ00_ZS / RHRHAZ00_ZX.
    Returns: DataFrame with columns: z_type, z_id, lang, text
    """
    path = DATA_DIR / filename
    header_idx = _find_header_row(path)
    buffer = _read_text_without_nuls(path)

    df = pd.read_csv(
        buffer,
        sep="\t",
        header=0,
        skiprows=header_idx,
        dtype=str,
        engine="c",
    )
    df.columns = [c.strip() for c in df.columns]

    df = df[df["TO"].str.strip() == z_type].copy()
    df["z_type"] = z_type
    df["z_id"] = df["ID obj."].str.strip()

    df["lang"] = df["VarPole"].str.strip().map({"C": "CS", "D": "DE", "E": "EN"})
    df["text"] = df["Var.pole uživatel.dat"].astype(str).str.strip()

    return df[["z_type", "z_id", "lang", "text"]]


def build_rhrhaz00_tables():
    """
    Convenience function to load all RHRHAZ00-related tables and return them
    in a dictionary.
    """
    # Person–Position
    person_position_history = load_rhrhaz00_ps(
        "250827_Export_AI_Skill_Coatch_RE_RHRHAZ00_P_S.txt"
    )

    # Dimensions
    persons = (
        person_position_history[["person_id"]]
        .drop_duplicates()
        .reset_index(drop=True)
    )
    positions = (
        person_position_history[["position_id"]]
        .drop_duplicates()
        .reset_index(drop=True)
    )

    # Position–Task
    position_tasks = load_rhrhaz00_st(
        "250828_Export_AI_Skill_Coatch_RE_RHRHAZ00_S_T.txt"
    )

    # Task–Z links
    task_zp_links = load_rhrhaz00_t_z(
        "250828_Export_AI_Skill_Coatch_RE_RHRHAZ00_T_ZP.txt", "ZP"
    )
    task_zs_links = load_rhrhaz00_t_z(
        "250828_Export_AI_Skill_Coatch_RE_RHRHAZ00_T_ZS.txt", "ZS"
    )
    task_zx_links = load_rhrhaz00_t_z(
        "250828_Export_AI_Skill_Coatch_RE_RHRHAZ00_T_ZX.txt", "ZX"
    )
    task_z_links = pd.concat(
        [task_zp_links, task_zs_links, task_zx_links],
        ignore_index=True,
    )

    # ZP descriptions from ZHRPD exports
    zp_cs = load_zhrpd_descr_zp(
        "250828_Export_AI_Skill_Coatch_ZHRPD_DESCR_EXPORT_CS.txt", "CS"
    )
    zp_de = load_zhrpd_descr_zp(
        "250828_Export_AI_Skill_Coatch_ZHRPD_DESCR_EXPORT_DE.txt", "DE"
    )
    zp_en = load_zhrpd_descr_zp(
        "250828_Export_AI_Skill_Coatch_ZHRPD_DESCR_EXPORT_EN.txt", "EN"
    )
    z_descr_zp = pd.concat([zp_cs, zp_de, zp_en], ignore_index=True)

    # ZS / ZX descriptions from RHRHAZ00
    zs_master = load_rhrhaz00_z_master(
        "250828_Export_AI_Skill_Coatch_RE_RHRHAZ00_ZS.txt", "ZS"
    )
    zx_master = load_rhrhaz00_z_master(
        "250828_Export_AI_Skill_Coatch_RE_RHRHAZ00_ZX.txt", "ZX"
    )

    z_descriptions = pd.concat(
        [z_descr_zp, zs_master, zx_master],
        ignore_index=True,
    )

    return {
        "persons": persons,
        "positions": positions,
        "person_position_history": person_position_history,
        "position_tasks": position_tasks,
        "task_z_links": task_z_links,
        "z_descriptions": z_descriptions,
    }