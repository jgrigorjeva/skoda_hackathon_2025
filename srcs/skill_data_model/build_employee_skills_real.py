import json
from pathlib import Path

import pandas as pd

from config import OUTPUT_DIR


def infer_level_from_count(n: int) -> str:
    """
    Simple heuristic to convert course count to skill level.
    Adjust thresholds as needed.
    """
    if n >= 3:
        return "Advanced"
    elif n == 2:
        return "Practitioner"
    elif n == 1:
        return "Beginner"
    else:
        return "None"


def build_employee_skills():
    # Paths to CSVs produced by main.py
    training_participation_path = OUTPUT_DIR / "training_participation.csv"
    training_events_path = OUTPUT_DIR / "training_events.csv"
    skill_mapping_path = OUTPUT_DIR / "skill_mapping.csv"
    degreed_learning_path = OUTPUT_DIR / "degreed_learning.csv"

    if not training_participation_path.exists() or not training_events_path.exists():
        raise FileNotFoundError(
            "training_participation.csv or training_events.csv not found. "
            "Run main.py first to generate output CSVs."
        )

    if not skill_mapping_path.exists():
        raise FileNotFoundError(
            "skill_mapping.csv not found. Run main.py first to generate output CSVs."
        )

    # Load data
    training_participation = pd.read_csv(
        training_participation_path,
        dtype=str,
        parse_dates=["start_date", "end_date"],
    )
    training_events = pd.read_csv(training_events_path, dtype=str)
    skill_mapping = pd.read_csv(skill_mapping_path, dtype=str)

    # Clean up columns
    for df in (training_participation, training_events, skill_mapping):
        df.columns = [c.strip() for c in df.columns]

    # skill_mapping: course_code -> skill_name
    # These are the columns we defined in the updated load_skill_mapping()
    skill_mapping["skill_name"] = skill_mapping["skill_name"].fillna("").str.strip()
    skill_mapping["course_code"] = skill_mapping["course_code"].fillna("").str.strip()
    skill_mapping = skill_mapping[skill_mapping["skill_name"] != ""].copy()

    # Assumption: event_type_id (Typ akce) == course_code (Zkratka D / course_code)
    course_to_skill = skill_mapping.set_index("course_code")["skill_name"]

    # Attach skill_name to participation via event_type_id
    training_participation["event_type_id"] = (
        training_participation["event_type_id"].astype(str).str.strip()
    )
    training_participation["skill_name"] = training_participation["event_type_id"].map(
        course_to_skill
    )

    # Keep only rows where we have a mapped skill_name
    training_participation_skills = training_participation.dropna(
        subset=["skill_name"]
    ).copy()

    # Count occurrences per person_id and skill_name
    counts = (
        training_participation_skills.groupby(["person_id", "skill_name"])
        .size()
        .reset_index(name="course_count")
    )

    # Convert counts to levels
    counts["course_count"] = counts["course_count"].astype(int)
    counts["level"] = counts["course_count"].apply(infer_level_from_count)

    # Optionally incorporate Degreed to bump some skills based on keywords
    degreed_skills = None
    if degreed_learning_path.exists():
        degreed = pd.read_csv(
            degreed_learning_path, dtype=str, parse_dates=["completed_date"]
        )
        degreed.columns = [c.strip() for c in degreed.columns]

        # Make sure we have the expected columns
        expected_cols = {"person_id", "content_title"}
        missing = expected_cols - set(degreed.columns)
        if missing:
            print(
                f"Warning: degreed_learning.csv is missing columns {missing}; "
                f"skipping Degreed-based skill inference."
            )
        else:
            degreed["person_id"] = degreed["person_id"].astype(str).str.strip()
            degreed["content_title"] = (
                degreed["content_title"].astype(str).str.lower()
            )

            # Basic keyword → skill_name mapping (adjust to your needs)
            keyword_to_skill = {
                "python": "Python",
                "mlops": "MLOps",
                "machine learning": "Machine Learning",
                "data quality": "Data Quality",
                "sql": "SQL",
                "ci/cd": "CI/CD",
                "git": "Version Control",
            }

            rows = []
            for keyword, skill_name in keyword_to_skill.items():
                mask = degreed["content_title"].str.contains(keyword)
                sub = degreed[mask].copy()
                if sub.empty:
                    continue
                grp = sub.groupby("person_id").size().reset_index(name="cnt")
                grp["skill_name"] = skill_name
                rows.append(grp)

            if rows:
                degreed_counts = pd.concat(rows, ignore_index=True)

                def degreed_level(n):
                    if n >= 5:
                        return "Advanced"
                    elif n >= 3:
                        return "Practitioner"
                    elif n >= 1:
                        return "Beginner"
                    else:
                        return "None"

                degreed_counts["cnt"] = degreed_counts["cnt"].astype(int)
                degreed_counts["level"] = degreed_counts["cnt"].apply(degreed_level)
                degreed_skills = degreed_counts

    # Build dictionary: employee_id -> {skill_name -> best_level}
    employee_skills = {}
    level_order = {"None": 0, "Beginner": 1, "Practitioner": 2, "Advanced": 3, "Expert": 4}

    def update_skill(person_id: str, skill_name: str, level: str):
        if person_id not in employee_skills:
            employee_skills[person_id] = {}
        current = employee_skills[person_id].get(skill_name, "None")
        if level_order.get(level, 0) > level_order.get(current, 0):
            employee_skills[person_id][skill_name] = level

    # From SAP course participation
    for _, row in counts.iterrows():
        pid = str(row["person_id"])
        skill_name = str(row["skill_name"])
        level = str(row["level"])
        update_skill(pid, skill_name, level)

    # From Degreed (optional)
    if degreed_skills is not None:
        for _, row in degreed_skills.iterrows():
            pid = str(row["person_id"])
            skill_name = str(row["skill_name"])
            level = str(row["level"])
            update_skill(pid, skill_name, level)

    # Convert to list of dicts
    employees_list = []
    for pid, skills_dict in employee_skills.items():
        employees_list.append({"employee_id": pid, "skills": skills_dict})

    output_path = Path("employee_skills.json")
    output_path.write_text(
        json.dumps(employees_list, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(
        f"Saved employee skills for {len(employees_list)} employees to {output_path.resolve()}"
    )


if __name__ == "__main__":
    build_employee_skills()