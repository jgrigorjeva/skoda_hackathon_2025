from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib import messages
from .logic.ai_comm import send_text_to_ai
import json
from .logic.parser import parse_strategy_md
from .logic import scoring
from .logic.roadmap import build_roadmap

def _load_json(name):
    with open(settings.DATA_DIR / name, 'r', encoding='utf-8') as f:
        return json.load(f)

def _load_text(name):
    with open(settings.DATA_DIR / name, 'r', encoding='utf-8') as f:
        return f.read()

def index(request):
    md = _load_text('strategy.md')
    extracted = parse_strategy_md(md)
    skills = _load_json('skills.json')
    employees = _load_json('employees.json')['employees']

    skills_map = {s['id']: s for s in skills.get('skills',[])}

    gap_blocks = []
    for cap in extracted.get('capabilities', []):
        for req in cap.get('required_skills', []):
            skill_id = req['skill_id']
            target_level = req['target_level']
            coverage = scoring.coverage_at_or_above(employees, skill_id, target_level)
            gap_blocks.append({
                'cap_id': cap['id'],
                'cap_name': cap['name'],
                'skill_id': skill_id,
                'skill_name': skills_map.get(skill_id,{}).get('name', skill_id),
                'target_level': target_level,
                'headcount_target': cap.get('headcount_target',1),
                'current_coverage': coverage,
                'deadline': cap.get('target_date','')
            })

    return render(request, 'planner/index.html', {
        'capabilities': extracted.get('capabilities', []),
        'gap_blocks': gap_blocks
    })

def candidates(request, cap_id, skill_id):
    md = _load_text('strategy.md')
    extracted = parse_strategy_md(md)
    cap = next((c for c in extracted.get('capabilities',[]) if c['id']==cap_id), None)
    if not cap:
        return render(request, 'planner/candidates.html', {'error': 'Capability not found'})

    req = next((r for r in cap.get('required_skills',[]) if r['skill_id']==skill_id), None)
    if not req:
        return render(request, 'planner/candidates.html', {'error': 'Skill requirement not found'})

    skills = _load_json('skills.json')
    employees = _load_json('employees.json')['employees']
    skills_map = {s['id']: s for s in skills.get('skills',[])}
    hours_per_step = skills.get('hours_per_step',{})

    deadline_months = scoring.months_until(cap.get('target_date','2099-12-31'))

    rows = []
    for e in employees:
        metrics = scoring.compute_candidate_metrics(
            e, skill_id, req['target_level'], skills_map, hours_per_step, deadline_months
        )
        rows.append(metrics)

    rows.sort(key=lambda r: (-r['readiness'], r['risk'], r['ttr_months'], r['name']))

    return render(request, 'planner/candidates.html', {
        'cap': cap,
        'skill_id': skill_id,
        'skill_name': skills_map.get(skill_id,{}).get('name', skill_id),
        'rows': rows
    })

def roadmap(request, cap_id, skill_id, emp_id):
    md = _load_text('strategy.md')
    extracted = parse_strategy_md(md)
    cap = next((c for c in extracted.get('capabilities',[]) if c['id']==cap_id), None)

    employees = _load_json('employees.json')['employees']
    emp = next((e for e in employees if e['id']==emp_id), None)

    skills = _load_json('skills.json')
    req = None
    if cap:
        req = next((r for r in cap.get('required_skills',[]) if r['skill_id']==skill_id), None)

    learning = _load_json('learning.json')

    plan = None
    if emp and req:
        plan = build_roadmap(emp, skill_id, req['target_level'], skills, learning)

    return render(request, 'planner/roadmap.html', {
        'cap': cap,
        'emp': emp,
        'skill_id': skill_id,
        'skill_name': next((s['name'] for s in skills.get('skills',[]) if s['id']==skill_id), skill_id),
        'target_level': req['target_level'] if req else '',
        'plan': plan
    })


def upload_strategy(request):
    """Handle uploaded text file, send content to AI module, and overwrite data/strategy.md."""
    if request.method != 'POST':
        return redirect('index')

    uploaded = request.FILES.get('file')
    if not uploaded:
        messages.error(request, 'No file uploaded')
        return redirect('index')

    # read uploaded bytes and decode safely
    try:
        raw = uploaded.read()
        text = raw.decode('utf-8')
    except Exception:
        try:
            text = raw.decode('latin-1')
        except Exception:
            messages.error(request, 'Could not decode uploaded file')
            return redirect('index')

    # send to AI module for processing (if configured)
    system_prompt = (
        "You are a strict formatter. Reshape the provided text into a Markdown document that EXACTLY follows this template:\n\n"
        "# Strategic Goals\n\n"
        "## Goal: <Goal Title>\n"
        "- id: cap.<short_id>\n"
        "- target_date: YYYY-MM-DD\n"
        "- headcount_target: N\n"
        "- required_skills:\n"
        "  - skill.<skill_id>: <Level>\n\n"
        "Repeat the structure for each goal. Use 'cap.' prefix for capability ids and 'skill.' for skill ids.\n"
        "If some fields are missing in the source, try to fill them based on average required skill set for required to reach such goals\n"
        "Return ONLY the Markdown document — no explanations, no extra text, no JSON wrappers. The output must start with '# Strategic Goals'."
    )

    processed = send_text_to_ai(
        text,
        system_message=system_prompt,
        max_tokens=2000,
        temperature=0.0,
    )

    # Stronger validation: parse the AI output and require at least one capability
    parsed = parse_strategy_md(processed or '')
    caps = parsed.get('capabilities', [])
    has_reqs = any(len(c.get('required_skills', [])) > 0 for c in caps)

    if not caps or not has_reqs:
        preview = (processed or '')[:1000]
        messages.error(request, 'AI output did not include any required_skills entries; not overwriting strategy.md.')
        if preview:
            messages.info(request, f'AI output preview:\n{preview}')
        return redirect('index')

    # overwrite the strategy.md file
    try:
        target = settings.DATA_DIR / 'strategy.md'
        with open(target, 'w', encoding='utf-8') as f:
            f.write(processed)
        messages.success(request, 'strategy.md updated successfully')
    except Exception as e:
        messages.error(request, f'Failed to write strategy.md: {e}')

    return redirect('index')
