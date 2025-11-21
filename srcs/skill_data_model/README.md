#the skill data model 
takes all the raw data (.txt and .xlxs files) in the data/ folder (needs to be added to the skill_data_model/). Then restructures them as .csv files when running this code 
```bash
python3 main.py
```
Then it builds the employee_skills.json
```bash
python3 build_employee_skills_real.py
```
And maps them to the skills required by the strategy.md
```bash
python3 generate_skill_mapping_with_llm.py <API-URL>  <API-KEY> 2025-01-01-preview hackathon-gpt-5.1 ./strategy.md ./employee_skills.json ./strategy_skill_mapping.json
```

(Replace the values in <> with the real URL and KEY).

It then scores the employees by their skill match with the skills defined in strategy.md and generates 50 best candidates to send to final selection to LLM API
```
python3 score_employees_for_strategy.py
```

Final selection:
```
python3 rank_employees_for_strategy.py <API-URL> <API-KEY> 2025-01-01-preview hackathon-gpt-5.1 ./strategy.md ./candidate_employees.json ./best_employees.json
```
Now we have selected 10 best candidates with their rankings and some verbose description in best_employees.json