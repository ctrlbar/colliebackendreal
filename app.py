import os
from flask import Flask, request, jsonify
from openai import OpenAI
import requests
import json
from gpa_scraper import scrape_college_gpa  

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

    # Extract user's GPA safely
    user_gpa_str = user_stats.get("GPA")
    try:
        user_gpa = float(user_gpa_str) if user_gpa_str else "unknown"
    except ValueError:
        user_gpa = "unknown"

    # Robustly call scraper and convert scraped_gpa to float
    try:
        scraped_gpa_result = scrape_college_gpa(college)
        scraped_gpa = scraped_gpa_result.get("gpa")
        scraped_gpa = float(scraped_gpa)
    except Exception as e:
        print(f"[DEBUG] scrape_college_gpa error or invalid GPA: {e}")
        scraped_gpa = None

    # Fallback logic using admission rate if GPA is missing or unusable
    if scraped_gpa is None or (
        isinstance(scraped_gpa, str) and (
            "error" in scraped_gpa.lower() or
            "not found" in scraped_gpa.lower()
        )
    ):
        # Fallback to estimate from admission rate
        search_url = "https://api.data.gov/ed/collegescorecard/v1/schools"
        params = {
            "api_key": COLLEGE_SCORECARD_API_KEY,
            "school.name": college,
            "fields": "id,school.name",
            "per_page": 1
        }

        resp = requests.get(search_url, params=params)
        results = resp.json().get("results")
        if results:
            college_id = results[0].get("id")
            info_url = "https://api.data.gov/ed/collegescorecard/v1/schools"
            info_params = {
                "api_key": COLLEGE_SCORECARD_API_KEY,
                "id": college_id,
                "fields": "latest.admissions.admission_rate.overall"
            }

            info_resp = requests.get(info_url, params=info_params)
            info_data = info_resp.json().get("results", [{}])[0]
            admission_rate = info_data.get("latest.admissions.admission_rate.overall")

            if admission_rate is not None:
                if admission_rate < 0.15:
                    scraped_gpa = 4.2
                elif admission_rate < 0.40:
                    scraped_gpa = 4.0
                else:
                    scraped_gpa = 3.7
            else:
                scraped_gpa = "not publicly available"
        else:
            scraped_gpa = "not publicly available"

    # Try converting to float if possible
    if isinstance(scraped_gpa, str):
        try:
            scraped_gpa = float(scraped_gpa)
        except ValueError:
            scraped_gpa = "not publicly available"

    system_prompt = {
        "role": "system",
        "content": (
            "You are Collie, an expert college advisor. "
            "Analyze the student's stats compared to their target college and provide "
            "a JSON array of category ratings for the application. Each object must have: "
            "\"title\" (string), \"score\" (0-100 number), and \"explanation\" (string). "
            "The 'Academics' explanation must clearly compare the student's GPA and SAT (if available) to the average GPA and SAT of the target college. "
            "Categories include: Academics, Extracurriculars, Honors, Uniqueness, and Impact. "
            "Return ONLY the JSON array, no extra text."
        )
    }

    user_content = (
        f"Analyze the student's profile compared to the college '{college}':\n"
        f"Stats: {user_stats}\n"
        f"Extracurriculars: {extracurriculars}\n"
        f"Honors: {honors}\n"
        f"Clubs: {clubs}\n"
        f"Intended major: {major}\n"
        f"The student GPA is {user_gpa} (unweighted, 4.0 scale). "
        f"The average GPA at {college} is {scraped_gpa} (may be weighted or unweighted depending on source).\n\n"
        "Note: The student's GPA is unweighted. If the college GPA appears higher than 4.0, it may be weighted. Adjust your analysis accordingly."
        "Return ONLY a JSON array of objects with keys: title, score (0-100), explanation."
    )

    messages = [
        system_prompt,
        {"role": "user", "content": user_content}
    ]

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0,
            max_tokens=700,
        )
    except Exception as e:
        return jsonify({"error": f"OpenAI API error: {str(e)}"}), 500

    content = response.choices[0].message.content.strip()
    
        # Remove markdown code block wrappers (```json ... ```)
    if content.startswith("```json") and content.endswith("```"):
        content = content[7:-3].strip()
    elif content.startswith("```") and content.endswith("```"):
        content = content[3:-3].strip()

    
    print("[DEBUG] GPT Response:\n", content)

    try:
        category_ratings = json.loads(content)
        if not isinstance(category_ratings, list):
            raise ValueError("Response is not a JSON array")
        for item in category_ratings:
            if not all(k in item for k in ("title", "score", "explanation")):
                raise ValueError("Missing keys in category rating item")
            if not isinstance(item["score"], (int, float)):
                raise ValueError("Score is not a number")
    except Exception as e:
        return jsonify({
            "error": f"Failed to parse GPT response as category ratings JSON: {str(e)}",
            "raw_response": content
        }), 500

    return jsonify({
        "college": college,
        "categoryRatings": category_ratings
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
            estimated_gpa = 4.2
            estimated_sat = estimated_sat or 1450
            expected_class_rank_percentile = "top 5%"
            expected_num_aps = "10+"
        elif admission_rate < 0.40:
            estimated_gpa = 4.0
            estimated_sat = estimated_sat or 1300
            expected_class_rank_percentile = "top 10–20%"
            expected_num_aps = "6–9"
        else:
            estimated_gpa = 3.7
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
