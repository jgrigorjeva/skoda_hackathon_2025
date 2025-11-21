from pathlib import Path
import json
import sys
import requests
from collections import Counter


def call_azure_openai(api_url, api_key, api_version, deployment_name, system_message, user_message):
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
    resp = requests.post(url, headers=headers, params=params, json=data)
    if resp.status_code != 200:
        raise RuntimeError(f"Error {resp.status_code}: {resp.text}")
    result = resp.json()
    return result["choices"][0]["message"]["content"]


def main():
    if len(sys.argv) != 8:
        print(
            "Usage: python generate_skill_mapping_with_llm.py "
            "<api_url> <api_key> <api_version> <deployment_name> "
            "<strategy_md_path> <employee_skills_json> <output_mapping_json>"
        )
        print("Example:")
        print(
            "  python generate_skill_mapping_with_llm.py "
            "https://aicc-fit-openai.openai.azure.com YOUR_KEY 2025-01-01-preview "
            "hackathon-gpt-5.1 ./strategy.md ./employee_skills.json ./strategy_skill_mapping.json"
        )
        sys.exit(1)

    api_url = sys.argv[1].rstrip("/")
    api_key = sys.argv[2]
    api_version = sys.argv[3]
    deployment_name = sys.argv[4]
    strategy_md_path = Path(sys.argv[5])
    employee_skills_path = Path(sys.argv[6])
    output_mapping_path = Path(sys.argv[7])

    if not strategy_md_path.exists():
        print(f"strategy_md_path not found: {strategy_md_path}")
        sys.exit(1)
    if not employee_skills_path.exists():
        print(f"employee_skills_json not found: {employee_skills_path}")
        sys.exit(1)

    strategy_text = strategy_md_path.read_text(encoding="utf-8")
    employee_skills_data = json.loads(employee_skills_path.read_text(encoding="utf-8"))

    # Collect unique skill names and their frequency
    counter = Counter()
    for emp in employee_skills_data:
        skills = emp.get("skills", {})
        for name in skills.keys():
            counter[name] += 1

    # To keep prompt reasonable, take top N most common skills
    TOP_SKILLS = 100
    top_skills = [name for name, _cnt in counter.most_common(TOP_SKILLS)]

    system_message = (
        "You are an HR skills mapping assistant.\n"
        "You will be given:\n"
        "- Strategic goals with required skill codes (like 'skill.mlops', 'skill.python').\n"
        "- A list of internal skill names used in an HR system (like 'Python', 'Machine Learning', 'SQL').\n"
        "Your job is to map each strategy skill code to the most relevant internal skill names.\n"
        "You must output ONLY valid JSON, nothing else.\n"
    )

    user_message = f"""

 Here is the strategy.md content: 
   
{strategy_text}
   
 Here is a list of internal skill names available in the HR data (top {len(top_skills)} by frequency): 
   
 {json.dumps(top_skills, ensure_ascii=False, indent=2)} 
   
 Task: 
   

    Identify all strategy skill codes in the strategy.md under 'required_skills' lines, e.g. 'skill.mlops', 'skill.python', 'skill.ci', 'skill.sql', etc.

   

    For each strategy skill code, choose zero or more internal skill names from the list that best represent that strategy skill. Use your best judgement; it's better to pick a few good matches than many weak matches.

   

    Output ONLY a single JSON object with this structure:

   
 {{
"mappings": [
{{
"strategy_skill_code": "skill.mlops",
"internal_skill_names": ["Machine Learning", "Python"]
}},
{{
"strategy_skill_code": "skill.python",
"internal_skill_names": ["Python"]
}}
// ... one object per strategy skill code ...
]
}} 
   
 Constraints: 

    internal_skill_names must be taken only from the provided list of internal skills.
    If there is no good match for a strategy skill code, use an empty list [] for that entry.
    Do NOT include comments (// ..) in the JSON; that was only to illustrate the format.
    Do NOT output any text before or after the JSON. """
    try:
        content = call_azure_openai(
            api_url=api_url,
            api_key=api_key,
            api_version=api_version,
            deployment_name=deployment_name,
            system_message=system_message,
            user_message=user_message,
        )
        # Validate JSON
        try:
            mapping_obj = json.loads(content)
            output_mapping_path.write_text(
                json.dumps(mapping_obj, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            print(f"Saved strategy skill mapping to {output_mapping_path.resolve()}")
        except json.JSONDecodeError:
            # If model didn't return clean JSON, save raw content for debugging
            output_mapping_path.write_text(content, encoding="utf-8")
            print(
                f"Warning: model output was not valid JSON. "
                f"Raw content saved to {output_mapping_path.resolve()}"
            )
    except RuntimeError as e:
        print(str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()