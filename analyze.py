import os
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# Replace this with your College Scorecard API key stored as env variable
COLLEGE_SCORECARD_API_KEY = os.getenv("9wDUlGiQYvNNzErBNxfdr1XlzGX6wxtXR2WCaDK0")

@app.route("/analyze/stats", methods=["POST"])
def analyze_stats():
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data received"}), 400

    college_name = data.get("college")
    user_stats = data.get("user_stats")

    if not college_name or not user_stats:
        return jsonify({"error": "Missing college name or user stats"}), 400

    # Step 1: Get college ID from College Scorecard API by college name
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

    # Step 2: Fetch average freshman GPA for that college
    gpa_url = "https://api.data.gov/ed/collegescorecard/v1/schools"
    gpa_params = {
        "api_key": COLLEGE_SCORECARD_API_KEY,
        "id": college_id,
        "fields": "latest.admissions.admission_rate.overall,latest.student.avg_gpa"
    }

    gpa_resp = requests.get(gpa_url, params=gpa_params)
    if gpa_resp.status_code != 200:
        return jsonify({"error": "Failed to fetch GPA data"}), 500

    gpa_data = gpa_resp.json().get("results", [{}])[0]
    avg_gpa = gpa_data.get("latest.student.avg_gpa")

    # Prepare response with user stats and college averages
    response = {
        "college": college_name,
        "college_id": college_id,
        "average_freshman_gpa": avg_gpa,
        "user_stats": user_stats,
        "message": "Comparison data ready (expand with more analysis logic)"
    }

    return jsonify(response)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port)
