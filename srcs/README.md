# HR Strategy Planner MVP (Django)

Minimal MVP:
- Parses `data/strategy.md` for strategic goals (regex-based).
- Loads `employees.json`, `skills.json`, `learning.json`.
- Index page shows capability × skill gaps.
- Click a gap to see ranked candidates (Readiness high → Risk low).
- Click a candidate to see a simple learning roadmap.

## create .env near .env_example

## Quickstart
```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Open http://127.0.0.1:8000/

## Data files
- data/strategy.md
- data/skills.json
- data/employees.json
- data/learning.json
