import requests
import sys
import json
from pathlib import Path


def call_azure_openai(
    api_url: str,
    api_key: str,
    api_version: str,
    deployment_name: str,
    system_message: str,
    user_message: str,
) -> str:
    """
    Call Azure OpenAI chat completions and return the message content.
    """
    headers = {
        "api-key": api_key,
        "Content-Type": "application/json",
    }

    params = {"api-version": api_version}

    data = {
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message},
        ]
    }

    url = f"{api_url}/openai/deployments/{deployment_name}/chat/completions"
    response = requests.post(url, headers=headers, params=params, json=data)

    if response.status_code != 200:
        raise RuntimeError(f"Error {response.status_code}: {response.text}")

    result = response.json()
    return result["choices"][0]["message"]["content"]


def main():
    if len(sys.argv) != 8:
        print(
            "Usage: python rank_employees_for_strategy.py "
            "<api_url> <api_key> <api_version> <deployment_name> "
            "<strategy_md_path> <candidate_employees_json> <output_json_path>"
        )
        print("Example:")
        print(
            "  python rank_employees_for_strategy.py "
            "https://aicc-fit-openai.openai.azure.com YOUR_KEY 2025-01-01-preview "
            "hackathon-gpt-5.1 ./strategy.md ./candidate_employees.json ./best_employees.json"
        )
        sys.exit(1)

    api_url = sys.argv[1].rstrip("/")
    api_key = sys.argv[2]
    api_version = sys.argv[3]
    deployment_name = sys.argv[4]
    strategy_md_path = Path(sys.argv[5])
    candidates_path = Path(sys.argv[6])
    output_json_path = Path(sys.argv[7])

    if not strategy_md_path.exists():
        print(f"strategy_md_path not found: {strategy_md_path}")
        sys.exit(1)
    if not candidates_path.exists():
        print(f"candidate_employees_json not found: {candidates_path}")
        sys.exit(1)

    strategy_text = strategy_md_path.read_text(encoding="utf-8")
    candidate_text = candidates_path.read_text(encoding="utf-8")

    system_message = (
        "You are an HR/skills analytics assistant.\n"
        "You receive strategic goals and a pre-scored list of candidate employees.\n"
        "Your job is to select the best 10 employees overall across all goals and "
        "return ONLY a single valid JSON document.\n"
    )

    user_message = f"""
Here is the content of strategy.md:

---
{strategy_text}
---

Here is a JSON object containing:
- goals: parsed from strategy.md
- candidates: a list of employees with precomputed scores

```json
{candidate_text}
```

The candidate JSON has this structure:

{{
  "goals": [
    {{
      "goal_name": "...",
      "id": "cap.ml_platform",
      "target_date": "2026-12-31",
      "headcount_target": 3,
      "required_skills": [
        {{
          "skill_code": "skill.mlops",
          "required_level": "Advanced"
        }},
        ...
      ]
    }},
    ...
  ],
  "candidates": [
    {{
      "employee_id": "4241",
      "overall_score": 1.8,
      "per_goal_scores": [
        {{
          "goal_id": "cap.ml_platform",
          "match_score": 0.9,
          "skill_matches": [
            {{
              "skill_code": "skill.mlops",
              "required_level": "Advanced",
              "inferred_level": "Advanced",
              "internal_skill_name": "MLOps",
              "score": 1.0
            }},
            ...
          ]
        }},
        ...
      ]
    }},
    ...
  ],
  "total_employees": 6648
}}

Task:

1) Interpret the goals and required skills from 'goals'.
2) Use the 'candidates' list and their per_goal_scores to decide which 10 employees
   are overall the best fit for the strategy across all goals.
   - Consider both overall_score and balance across goals.
   - It is OK if an employee is a very strong fit for one goal and weaker for others.

3) Output ONLY a single JSON document with this structure:

{{
  "goals": [
    {{
      "goal_id": "<id from strategy.md>",
      "target_date": "<ISO date string>",
      "headcount_target": <integer>,
      "required_skills": [
        {{
          "skill_code": "<e.g. skill.mlops>",
          "required_level": "<e.g. Advanced>",
          "description_if_known": null
        }}
      ],
      "per_employee_scores": [
        {{
          "employee_id": "<employee_id>",
          "match_score": <number between 0 and 1>,
          "skill_matches": [
            {{
              "skill_code": "<e.g. skill.mlops>",
              "required_level": "<e.g. Advanced>",
              "inferred_level": "<e.g. Advanced>",
              "evidence": [
                "from pre-scoring: internal skill MLOps with level Advanced"
              ]
            }}
          ]
        }}
      ]
    }}
  ],
  "top_employees_overall": [
    {{
      "employee_id": "<ID>",
      "overall_match_score": <number between 0 and 1>,
      "best_fit_goals": [
        {{
          "goal_id": "<goal id>",
          "match_score": <number between 0 and 1>
        }}
      ],
      "summary_reasoning": "2–4 sentences summarising why this person is a strong fit."
    }}
  ]
}}

Constraints:

- 'top_employees_overall' MUST contain exactly 10 unique employees
  (unless there are fewer than 10 in the candidates list).
- Use the existing numeric scores as strong guidance; you may break ties
  or slightly reorder based on your reasoning.
- Ensure the JSON is syntactically valid (no trailing commas, correct quoting).
- Do NOT output any text outside the JSON.
"""

    try:
        content = call_azure_openai(
            api_url=api_url,
            api_key=api_key,
            api_version=api_version,
            deployment_name=deployment_name,
            system_message=system_message,
            user_message=user_message,
        )

        # Try to parse JSON; if it fails, save raw content for debugging.
        try:
            parsed = json.loads(content)
            output_json_path.write_text(
                json.dumps(parsed, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            print(f"Saved valid JSON result to {output_json_path.resolve()}")
        except json.JSONDecodeError:
            output_json_path.write_text(content, encoding="utf-8")
            print(
                f"Warning: model output was not valid JSON. "
                f"Raw content saved to {output_json_path.resolve()}"
            )

    except RuntimeError as e:
        print(str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
