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

Your job is to help users estimate their chances of getting into a specific college and offer helpful guidance.

When asked something like “What are my chances at UIUC?”, recognize that “UIUC” is the college. Only ask for the college if it hasn’t been mentioned yet.

To estimate admission chances, collect:
1. College name (if not mentioned)
2. GPA
3. SAT/ACT score (or if not submitting)
4. Extracurriculars
5. Intended major

If a college's average GPA or SAT/ACT score is not available, estimate them using these fallback rules:
- If admission rate < 15% → assume GPA 3.9+, SAT 1450+
- If admission rate between 15% and 40% → assume GPA 3.7, SAT 1300
- If admission rate > 40% → assume GPA 3.3, SAT 1150

LOOK THROUGH MEMORY TO AVOID BEING REDUNDANT IN ASKING QUESTIONS.

Give your response in a helpful, clear tone. Try to be concise. ALWAYS GIVE A PERCENTAGE ESTIMATE for how likely the student is to get into the selected college.
"""
}

@app.route("/api", methods=["POST"])
def chat():
    try:
        data = request.get_json()

        prompt = data.get("prompt", "").strip()
        session_id = data.get("session_id")

        if not client.api_key:
            return jsonify({"error": "API key not configured"}), 500

        if not prompt:
            return jsonify({"error": "Prompt cannot be empty"}), 400

        # If no session_id, create a new one and initialize conversation
        if not session_id:
            session_id = str(uuid.uuid4())
            conversations[session_id] = [SYSTEM_PROMPT]
        elif session_id not in conversations:
            # If session_id sent but unknown, also initialize
            conversations[session_id] = [SYSTEM_PROMPT]

        # Append user's message
        conversations[session_id].append({"role": "user", "content": prompt})

        # Call OpenAI chat completion API with full conversation history
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=conversations[session_id]
        )

        answer = response.choices[0].message.content.strip()

        # Append assistant's reply to conversation history
        conversations[session_id].append({"role": "assistant", "content": answer})

        # Return answer AND session_id (so client can save it)
        return jsonify({"answer": answer, "session_id": session_id})

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

    # Step 1: Get college ID
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

    # Step 2: Fetch admission rate and SAT average
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

    # Fallback estimates if missing
    estimated_gpa = None
    estimated_sat = avg_sat

    if admission_rate is not None:
        if admission_rate < 0.15:
            estimated_gpa = 3.9
            if not avg_sat:
                estimated_sat = 1450
        elif admission_rate < 0.40:
            estimated_gpa = 3.7
            if not avg_sat:
                estimated_sat = 1300
        else:
            estimated_gpa = 3.3
            if not avg_sat:
                estimated_sat = 1150
    else:
        # No admission rate available
        estimated_gpa = "unknown"
        estimated_sat = estimated_sat or "unknown"

    response = {
        "college": college_name,
        "college_id": college_id,
        "admission_rate": admission_rate,
        "average_sat": avg_sat,
        "estimated_gpa_based_on_selectivity": estimated_gpa,
        "used_fallback_sat": avg_sat is None,
        "user_stats": user_stats,
        "message": "Comparison data ready with fallback estimates if needed"
    }

    return jsonify(response)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
