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
    "content": """You are Collie, an expert AI college advisor.

Speak directly to the student using second-person voice (“you”) as if you’re giving them personalized advice.

To estimate their chances of getting into a college, review the following if provided:
1. College name and its selectivity
2. GPA
3. SAT/ACT score 
4. Class rank and AP count
5. Extracurriculars, honors & awards, and clubs
6. Intended major

If GPA, SAT/ACT, or AP count is missing, use the following fallback estimates based on admission rate:
- < 15% → GPA 3.9+, SAT 1450+, ACT 33+, top 5%, 10+ APs
- 15–40% → GPA 3.7, SAT 1300, ACT 28, top 10–20%, 6–9 APs
- > 40% → GPA 3.3, SAT 1150, ACT 23, top 30–40%, 3–5 APs

Give the user a short, clear summary that highlights where they are strong and where they could improve. End with a realistic admission chance (as a percentage)."
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

        prompt = f"Provide a summary comparing a student's stats to {college}. "
        prompt += f"Student Major: {major}. "  # <-- Add major here
        prompt += f"Student GPA: {user_stats.get('GPA', 'N/A')}, "
        prompt += f"SAT Score: {user_stats.get('SAT Score', 'N/A')}, "
        prompt += f"Extracurriculars: {extracurriculars}, Honors: {honors}, Clubs: {clubs}. "

        if average_gpa is not None:
            prompt += f"Average GPA at school: {average_gpa:.2f}. "
        if admission_rate is not None:
            prompt += f"Admission rate: {admission_rate * 100:.1f}%. "

        prompt += "Based on this data, provide a concise summary and likelihood of admission."

        messages = [SYSTEM_PROMPT, {"role": "user", "content": prompt}]
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages
        )

        answer = response.choices[0].message.content.strip()
        return jsonify({"summary": answer})

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
