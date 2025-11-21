from typing import Dict, Any, List

def build_roadmap(emp: Dict[str,Any], skill_id: str, target_level: str, skills: Dict[str,Any], courses_data: Dict[str,Any]) -> Dict[str,Any]:
    levels = ['Novice','Practitioner','Advanced','Expert']
    def lnum(l):
        try: return levels.index(l)
        except ValueError: return 0

    curr = 0
    for s in emp.get('skills', []):
        if s['skill_id'] == skill_id:
            curr = lnum(s['level']); break
    tgt = lnum(target_level)
    steps = max(0, tgt - curr)

    courses = courses_data.get('courses', [])
    mentors = courses_data.get('mentors', [])

    plan: List[Dict[str,Any]] = []
    skill = next((sk for sk in skills.get('skills', []) if sk['id']==skill_id), {'prereqs':[]})

    for p in skill.get('prereqs', []):
        c = next((x for x in courses if x['skill_id']==p), None)
        if c:
            plan.append({'type':'course','title':c['title'],'hours':c.get('hours',20),'skill_id':p})

    main_courses = [c for c in courses if c['skill_id']==skill_id]
    if main_courses:
        chosen = sorted(main_courses, key=lambda x: -x.get('hours', 0))[0]
        plan.append({'type':'course','title':chosen['title'],'hours':chosen.get('hours', 40),'skill_id':skill_id})
    elif steps>0:
        plan.append({'type':'course','title':f'Self-study: {skill_id}','hours':40*steps,'skill_id':skill_id})

    total_course_hours = sum(x['hours'] for x in plan if x['type']=='course')
    m = next((m for m in mentors if skill_id in m.get('skills',[])), None)
    if m and total_course_hours>0:
        plan.append({'type':'mentoring','title':f"Mentor: {m['name']}",'hours':int(0.2*total_course_hours)})

    plan.append({'type':'project','title':'On-the-job task: apply skill on live initiative','hours':20})

    return {'steps': plan, 'expected_uplift': f"{levels[curr]}→{levels[tgt]}" }
