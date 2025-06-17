import os
from flask import Flask, request, jsonify
from openai import OpenAI

app = Flask(__name__)

client = OpenAI()

@app.route("/api", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        prompt = data.get("prompt", "")

        if not client.api_key:
            return jsonify({"error": "API key not configured"}), 500

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": """You are Collie, an expert AI college advisor.

Your built in first message is:
"Hi! I'm Collie, your AI College Advisor. Want to find out your chances at a college? Or have questions?"
No need to greet again.

If asked about chances, ask these one by one (tailored to the college):

GPA?

SAT/ACT score? (or note if not submitting)

Extracurriculars?

Preferred major?

Then, give a clear, friendly estimate of admission chances with actionable tips if needed.

For other questions, offer expert, warm, concise advice.

"""},
                {"role": "user", "content": prompt}
            ],
        )
        answer = response.choices[0].message.content.strip()

        return jsonify({"answer": answer})

    except Exception as e:
        print("Error occurred:", str(e))
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))