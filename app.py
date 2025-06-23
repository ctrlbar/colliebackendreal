import os
import uuid
from flask import Flask, request, jsonify
from openai import OpenAI
import requests

app = Flask(__name__)
client = OpenAI()

conversations = {}

SYSTEM_PROMPT = {
    "role": "system",
    "content": """You're Collie, an expert college advisor focused on helping students strengthen their college applications.

Your job is to:
- Analyze the student's stats in comparison to their target college
- Identify clear *weaknesses or missing pieces*
- Give *specific, actionable suggestions* on what to improve (e.g., "Your GPA is slightly below average for MIT; consider taking additional APs or dual enrollment courses", or "You lack leadership experience; look for a club position or start a project")
- Avoid fluff and encouragement — focus on practical advice
- Only include strengths if they’re necessary for contrast
- End with a realistic next step or strategy to improve admission odds

You are NOT generating a summary or acceptance likelihood, only an improvement analysis.
"""
}

@app.route("/api/gpt-summary", methods=["POST"])
def gpt_summary():
    try:
        data = request.get_json()

        college = data.get("college")
        user_stats = data.get("user_stats", {})
        extracurriculars = data.get("extracurriculars", "")
        honors = data.get("honors", "")
        major = data.get("major", "N/A")
        clubs = data.get("clubs", "")
        admission_rate = data.get("admission_rate")
        average_gpa = data.get("average_gpa")

        if not college or not user_stats:
            return jsonify({"error": "Missing college or user stats"}), 400

        prompt = f"""Here is a student's college application profile:

College: {college}
Major: {major}
GPA: {user_stats.get('GPA', 'N/A')}
SAT: {user_stats.get('SAT Score', 'N/A')}
ACT: {user_stats.get('ACT Score', 'N/A')}
Extracurriculars: {extracurriculars}
Honors and Awards: {honors}
Clubs/Other: {clubs}
Average GPA at college: {average_gpa if average_gpa is not None else 'N/A'}
Admission rate: {admission_rate * 100:.1f}% if known

Please provide a JSON array of category ratings like this:

[
  {{ "title": "Academics", "score": 80, "explanation": "Strong GPA, but SAT could be improved." }},
  {{ "title": "Extracurriculars", "score": 65, "explanation": "Has multiple clubs, could use more leadership." }},
  {{ "title": "Honors and Awards", "score": 50, "explanation": "Few listed, consider entering competitions." }},
  {{ "title": "Uniqueness", "score": 40, "explanation": "Standard profile. Add a unique project or initiative." }},
  {{ "title": "Impact", "score": 55, "explanation": "Good foundation. Expand volunteering or public work." }}
]

Return **only** the JSON array with no introduction or extra text.
"""

        messages = [
            {
                "role": "system",
                "content": "You are an expert college admissions advisor. Respond with only the JSON array of category ratings as described."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages
        )

        answer = response.choices[0].message.content.strip()

        # Try parsing the JSON response
        import json
        try:
            ratings = json.loads(answer)
        except json.JSONDecodeError as e:
            print("Failed to parse GPT JSON:", answer)
            return jsonify({"error": "GPT response was not valid JSON"}), 500

        return jsonify(ratings)

    except Exception as e:
        print("Error occurred:", str(e))
        return jsonify({"error": str(e)}), 500


COLLEGE_SCORECARD_API_KEY = os.getenv("COLLEGE_SCORECARD_API_KEY")

@app.route("/analyze/stats", methods=["POST"])
def analyze_stats():
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data received"}), 400

    college_name = data.get("college")
    user_stats = data.get("user_stats")

    if not college_name or not user_stats:
        return jsonify({"error": "Missing college name or user stats"}), 400

    search_url = "https://api.data.gov/ed/collegescorecard/v1/schools"
    params = {
        "api_key": COLLEGE_SCORECARD_API_KEY,
        "school.name": college_name,
        "fields": "id,school.name",
        "per_page": 1
    }

    resp = requests.get(search_url, params=params)
    if resp.status_code != 200:
        return jsonify({"error": "Failed to fetch college info"}), 500

    results = resp.json().get("results")
    if not results:
        return jsonify({"error": f"College '{college_name}' not found"}), 404

    college_id = results[0].get("id")

    info_url = "https://api.data.gov/ed/collegescorecard/v1/schools"
    info_params = {
        "api_key": COLLEGE_SCORECARD_API_KEY,
        "id": college_id,
        "fields": "latest.admissions.admission_rate.overall,latest.admissions.sat_scores.average.overall"
    }

    info_resp = requests.get(info_url, params=info_params)
    if info_resp.status_code != 200:
        return jsonify({"error": "Failed to fetch admission data"}), 500

    info_data = info_resp.json().get("results", [{}])[0]
    admission_rate = info_data.get("latest.admissions.admission_rate.overall")
    avg_sat = info_data.get("latest.admissions.sat_scores.average.overall")

    estimated_gpa = None
    estimated_sat = avg_sat
    expected_class_rank_percentile = None
    expected_num_aps = None

    if admission_rate is not None:
        if admission_rate < 0.15:
            estimated_gpa = 3.9
            estimated_sat = estimated_sat or 1450
            expected_class_rank_percentile = "top 5%"
            expected_num_aps = "10+"
        elif admission_rate < 0.40:
            estimated_gpa = 3.7
            estimated_sat = estimated_sat or 1300
            expected_class_rank_percentile = "top 10–20%"
            expected_num_aps = "6–9"
        else:
            estimated_gpa = 3.3
            estimated_sat = estimated_sat or 1150
            expected_class_rank_percentile = "top 30–40%"
            expected_num_aps = "3–5"
    else:
        estimated_gpa = "unknown"
        estimated_sat = estimated_sat or "unknown"
        expected_class_rank_percentile = "unknown"
        expected_num_aps = "unknown"

    response = {
        "college": college_name,
        "college_id": college_id,
        "admission_rate": admission_rate,
        "average_sat": avg_sat,
        "estimated_gpa_based_on_selectivity": estimated_gpa,
        "expected_class_rank_percentile": expected_class_rank_percentile,
        "expected_num_aps": expected_num_aps,
        "used_fallback_sat": avg_sat is None,
        "user_stats": user_stats,
        "message": "Comparison data ready with fallback estimates if needed"
    }

    return jsonify(response)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
