import os
from flask import Flask, request, jsonify
from openai import OpenAI
import requests
import json

app = Flask(__name__)
client = OpenAI()

# Concise system prompt focusing only on improvement advice, no summary or score
SYSTEM_PROMPT = {
    "role": "system",
    "content": (
        "You are Collie, an expert college advisor. "
        "Analyze the student's stats compared to their target college and "
        "provide clear, specific, actionable advice to improve their application. "
        "Do NOT provide any summary, acceptance likelihood, or scores. "
        "Return ONLY a JSON object with a single key 'advice' containing a string."
    )
}

COLLEGE_SCORECARD_API_KEY = os.getenv("COLLEGE_SCORECARD_API_KEY")

@app.route("/api/gpt-summary", methods=["POST"])
def gpt_summary():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data received"}), 400

    college = data.get("college")
    user_stats = data.get("user_stats")
    extracurriculars = data.get("extracurriculars", "")
    honors = data.get("honors", "")
    clubs = data.get("clubs", "")
    major = data.get("major", "N/A")

    if not college or not user_stats:
        return jsonify({"error": "Missing college or user_stats"}), 400

    # Compose the user prompt with all info but no request for summary or scores
    user_content = (
        f"Analyze the student's profile compared to the college '{college}':\n"
        f"Stats: {user_stats}\n"
        f"Extracurriculars: {extracurriculars}\n"
        f"Honors: {honors}\n"
        f"Clubs: {clubs}\n"
        f"Intended major: {major}\n\n"
        "Provide ONLY a JSON object with the key 'advice' containing specific, actionable suggestions "
        "to improve their college application. No other text, no summary or score."
    )

    messages = [
        SYSTEM_PROMPT,
        {"role": "user", "content": user_content}
    ]

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0,
            max_tokens=500,
        )
    except Exception as e:
        return jsonify({"error": f"OpenAI API error: {str(e)}"}), 500

    content = response.choices[0].message.content.strip()

    # Attempt to parse JSON safely
    try:
        json_response = json.loads(content)
        advice = json_response.get("advice")
        if not isinstance(advice, str):
            raise ValueError("Invalid JSON: 'advice' key missing or not a string")
    except Exception:
        return jsonify({
            "error": "Failed to parse GPT response as valid JSON with key 'advice'",
            "raw_response": content
        }), 500

    return jsonify({
        "college": college,
        "advice": advice
    })


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
