import json
from pathlib import Path
import re
from typing import Dict, List


LEVEL_VALUE = {
    "None": 0.0,
    "Beginner": 0.4,
    "Practitioner": 0.7,
    "Advanced": 1.0,
    "Expert": 1.1,  # slight bonus if above required
}

# Map strategy skill codes to internal skill names in employee_skills.json
# Will be loaded from strategy_skill_mapping.json at runtime
STRATEGY_SKILL_TO_INTERNAL = {}


def parse_strategy(strategy_text: str) -> List[Dict]:
    """
    Parse strategy.md into structured goals.
    """
    lines = strategy_text.splitlines()
    goals = []
    current_goal = None
    in_required_skills = False

    goal_header_re = re.compile(r"^##\s+Goal:\s*(.+)")
    id_re = re.compile(r"^-+\s*id:\s*(.+)")
    target_re = re.compile(r"^-+\s*target_date:\s*(.+)")
    headcount_re = re.compile(r"^-+\s*headcount_target:\s*(\d+)")
    skill_line_re = re.compile(r"^\s*-\s*([a-zA-Z0-9_.]+)\s*:\s*([A-Za-z]+)", re.UNICODE)

    for raw_line in lines:
        line = raw_line.rstrip()

        m_goal = goal_header_re.match(line)
        if m_goal:
            if current_goal:
                goals.append(current_goal)
            current_goal = {
                "goal_name": m_goal.group(1).strip(),
                "id": None,
                "target_date": None,
                "headcount_target": None,
                "required_skills": [],
            }
            in_required_skills = False
            continue

        if current_goal is None:
            continue

        m_id = id_re.match(line)
        if m_id:
            current_goal["id"] = m_id.group(1).strip()
            continue

        m_target = target_re.match(line)
        if m_target:
            current_goal["target_date"] = m_target.group(1).strip()
            continue

        m_head = headcount_re.match(line)
        if m_head:
            current_goal["headcount_target"] = int(m_head.group(1))
            continue

        if "required_skills:" in line:
            in_required_skills = True
            continue

        if in_required_skills:
            m_skill = skill_line_re.match(line)
            if m_skill:
                skill_code = m_skill.group(1).strip()
                level = m_skill.group(2).strip().capitalize()
                current_goal["required_skills"].append(
                    {"skill_code": skill_code, "required_level": level}
                )

    if current_goal:
        goals.append(current_goal)

    return goals


def level_to_value(level: str) -> float:
    return LEVEL_VALUE.get(level, 0.0)


def required_level_value(level: str) -> float:
    mapping = {
        "Beginner": 0.4,
        "Practitioner": 0.7,
        "Advanced": 1.0,
        "Expert": 1.1,
    }
    return mapping.get(level, 0.0)


def compute_match(
    employee_skills: Dict[str, str],
    required_skills: List[Dict]
) -> Dict:
    """
    Compute match score for one employee vs one goal.
    """
    details = []
    scores = []

    # Precompute lowercase map
    lower_map = {name.lower(): (name, lvl) for name, lvl in employee_skills.items()}

    for rs in required_skills:
        skill_code = rs["skill_code"]
        req_level = rs["required_level"]

        internal_names = STRATEGY_SKILL_TO_INTERNAL.get(skill_code, [])
        best_level_value = 0.0
        best_level_name = "None"
        best_internal_name = None

        # Exact matches
        for name in internal_names:
            lvl = employee_skills.get(name)
            if not lvl:
                continue
            val = level_to_value(lvl)
            if val > best_level_value:
                best_level_value = val
                best_level_name = lvl
                best_internal_name = name

        # Fuzzy matching
        if best_internal_name is None:
            code_l = skill_code.lower()

            for in_name_l, (orig_name, lvl) in lower_map.items():
                val = 0.0

                if "python" in code_l and "python" in in_name_l:
                    val = level_to_value(lvl)
                elif "mlops" in code_l and (
                    "mlops" in in_name_l or "machine learning" in in_name_l
                ):
                    val = level_to_value(lvl)
                elif "ci" in code_l and (
                    "ci/cd" in in_name_l
                    or "continuous integration" in in_name_l
                    or "version control" in in_name_l
                    or "devops" in in_name_l
                ):
                    val = level_to_value(lvl)
                elif "sql" in code_l and "sql" in in_name_l:
                    val = level_to_value(lvl)

                if val > best_level_value:
                    best_level_value = val
                    best_level_name = lvl
                    best_internal_name = orig_name

        req_val = required_level_value(req_level)
        skill_score = min(best_level_value / req_val, 1.0) if req_val > 0 else 0.0

        scores.append(skill_score)
        details.append(
            {
                "skill_code": skill_code,
                "required_level": req_level,
                "inferred_level": best_level_name,
                "internal_skill_name": best_internal_name,
                "score": skill_score,
            }
        )

    overall = sum(scores) / len(scores) if scores else 0.0
    return {"match_score": overall, "skill_matches": details}


def main():
    base_dir = Path(".")
    strategy_path = base_dir / "strategy.md"
    employee_skills_path = base_dir / "employee_skills.json"
    output_path = base_dir / "candidate_employees.json"

    if not strategy_path.exists():
        raise FileNotFoundError(f"strategy.md not found at {strategy_path.resolve()}")
    if not employee_skills_path.exists():
        raise FileNotFoundError(
            f"employee_skills.json not found at {employee_skills_path.resolve()}"
        )

    strategy_text = strategy_path.read_text(encoding="utf-8")
    employee_skills_data = json.loads(
        employee_skills_path.read_text(encoding="utf-8")
    )

    goals = parse_strategy(strategy_text)
    print(f"Parsed {len(goals)} goals from strategy.md")

    for g in goals:
        print("DEBUG goal:", g["id"], "required_skills:", g["required_skills"])

    candidates = []

    for emp in employee_skills_data:
        emp_id = emp["employee_id"]
        skills = emp.get("skills", {})
        per_goal = []
        combined_score = 0.0

        for goal in goals:
            res = compute_match(skills, goal["required_skills"])
            per_goal.append(
                {
                    "goal_id": goal["id"],
                    "match_score": res["match_score"],
                    "skill_matches": res["skill_matches"],
                }
            )
            combined_score += res["match_score"]

        candidates.append(
            {
                "employee_id": emp_id,
                "overall_score": combined_score,
                "per_goal_scores": per_goal,
            }
        )

    candidates_sorted = sorted(
        candidates, key=lambda x: x["overall_score"], reverse=True
    )

    TOP_N = 50
    top_candidates = candidates_sorted[:TOP_N]

    output = {
        "goals": goals,
        "candidates": top_candidates,
        "total_employees": len(employee_skills_data),
    }

    output_path.write_text(
        json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(
        f"Saved {len(top_candidates)} top candidates "
        f"out of {len(employee_skills_data)} employees to {output_path.resolve()}"
    )


if __name__ == "__main__":
    main()
