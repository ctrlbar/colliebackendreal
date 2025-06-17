import os
import uuid
from flask import Flask, request, jsonify
from openai import OpenAI

app = Flask(__name__)
client = OpenAI()

conversations = {}

SYSTEM_PROMPT = {
    "role": "system",
    "content": """You are Collie, an expert AI college advisor.

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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
