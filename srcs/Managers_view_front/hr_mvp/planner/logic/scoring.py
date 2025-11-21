from typing import List, Dict, Any
from datetime import date
import math

LEVELS = ['Novice','Practitioner','Advanced','Expert']
LEVEL_INDEX = {lvl:i for i,lvl in enumerate(LEVELS)}

def months_until(target_date_str: str) -> float:
    y, m, d = [int(x) for x in target_date_str.split('-')]
    today = date.today()
    months = (y - today.year) * 12 + (m - today.month) + (d - today.day)/30.0
    return max(0.0, months)

def level_num(level: str) -> int:
    return LEVEL_INDEX.get(level, 0)

def calc_gap_steps(curr_level: int, target_level: int) -> int:
    return max(0, target_level - curr_level)

def sum_hours_for_steps(hours_per_step: Dict[str,int], steps: int, start_level: int) -> int:
    levels = LEVELS[:]
    total = 0
    for s in range(steps):
        frm = levels[start_level + s]
        to = levels[start_level + s + 1]
        key = f'{frm}→{to}'
        total += int(hours_per_step.get(key, 40))
    return total

def readiness_from_ttr(ttr_months: float) -> int:
    return max(0, min(100, int(round(100 - 15 * ttr_months))))

def sigmoid(x: float) -> float:
    return 1/(1+math.exp(-x))

def compute_candidate_metrics(emp: Dict[str,Any], skill_id: str, target_level: str,
                              skills_map: Dict[str,Any], hours_per_step: Dict[str,int],
                              deadline_months: float) -> Dict[str,Any]:
    current_level = 0
    for s in emp.get('skills', []):
        if s['skill_id'] == skill_id:
            current_level = level_num(s['level'])
            break
    target_level_num = level_num(target_level)
    gap_steps = calc_gap_steps(current_level, target_level_num)
    base_hours = sum_hours_for_steps(hours_per_step, gap_steps, current_level)

    skill = skills_map.get(skill_id, {})
    unmet_prereqs = [p for p in skill.get('prereqs', []) if not any(sp['skill_id']==p for sp in emp.get('skills',[]))]
    tax = 0.2 * len(unmet_prereqs)
    total_hours = int(round(base_hours * (1 + tax)))

    workload = float(emp.get('workload_pct', 0.8))
    available_per_month = max(8.0, (1.0 - workload) * 160.0)
    ttr = total_hours / available_per_month if available_per_month > 0 else 99.0

    readiness = readiness_from_ttr(ttr)

    delivery_risk = 0.0
    if ttr > deadline_months:
        delivery_risk = sigmoid((ttr - deadline_months)/3.0) * 100.0
    overutil = max(0.0, workload - 0.85) * (100.0 / 0.15)
    attrition = float(emp.get('attrition_prob', 0.2)) * 100.0
    risk = 0.5*delivery_risk + 0.35*attrition + 0.15*overutil

    reasons = []
    if gap_steps>0:
        reasons.append(f'Gap: {skill_id} {LEVELS[current_level]}→{LEVELS[target_level_num]} ({gap_steps} step(s))')
    if unmet_prereqs:
        reasons.append('Unmet prereqs: ' + ', '.join(unmet_prereqs))
    reasons.append(f'Workload {int(workload*100)}%')
    reasons.append(f'TTR ~ {ttr:.1f} mo vs deadline {deadline_months:.1f} mo')

    return {
        'employee_id': emp['id'],
        'name': emp.get('name',''),
        'role': emp.get('role',''),
        'current_level': LEVELS[current_level],
        'target_level': target_level,
        'gap_steps': gap_steps,
        'total_hours': total_hours,
        'ttr_months': round(ttr,1),
        'readiness': readiness,
        'risk': int(round(risk)),
        'reasons': reasons
    }


def coverage_at_or_above(employees: List[Dict[str,Any]], skill_id: str, target_level: str) -> int:
    tnum = level_num(target_level)
    c = 0
    for e in employees:
        lvl = 0
        for s in e.get('skills', []):
            if s['skill_id'] == skill_id:
                lvl = level_num(s['level'])
                break
        if lvl >= tnum:
            c += 1
    return c
