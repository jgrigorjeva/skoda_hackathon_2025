import re
from typing import Dict, Any

def parse_strategy_md(md_text: str) -> Dict[str, Any]:
    lines = md_text.splitlines()
    capabilities = []
    i = 0
    current = None
    reqs = []

    goal_re = re.compile(r'^##\s*Goal:\s*(.+)$', re.IGNORECASE)
    kv_re = re.compile(r'^-\s*(id|target_date|headcount_target):\s*(.+)$', re.IGNORECASE)
    skill_re = re.compile(r'^\s*-\s*([\w\.]+):\s*(\w+)$')

    while i < len(lines):
        line = lines[i].rstrip()
        g = goal_re.match(line)
        if g:
            if current:
                if reqs:
                    current['required_skills'] = reqs
                capabilities.append(current)
            current = {'name': g.group(1).strip(), 'required_skills': []}
            reqs = []
            i += 1
            continue

        if current:
            m = kv_re.match(line)
            if m:
                key = m.group(1).lower()
                val = m.group(2).strip()
                if key == 'headcount_target':
                    try:
                        val = int(val)
                    except ValueError:
                        val = 1
                current[key] = val
                i += 1
                continue

            if line.strip().lower().startswith('- required_skills'):
                i += 1
                while i < len(lines) and (lines[i].startswith('  ') or lines[i].startswith('\t') or lines[i].strip().startswith('-')):
                    item = lines[i].strip()
                    sm = skill_re.match(item)
                    if sm:
                        reqs.append({'skill_id': sm.group(1).strip(), 'target_level': sm.group(2).strip()})
                    i += 1
                continue
        i += 1

    if current:
        if reqs:
            current['required_skills'] = reqs
        capabilities.append(current)

    import re as _re
    for c in capabilities:
        if 'id' not in c:
            slug = _re.sub(r'[^a-z0-9]+', '_', c['name'].lower())
            c['id'] = f'cap.{slug}'.strip('.')
    return {'capabilities': capabilities}
