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

Your job is to help users estimate their chances of getting into a specific college and offer helpful guidance.

When asked something like “What are my chances at UIUC?”, recognize that “UIUC” is the college. Only ask for the college if it hasn’t been mentioned yet.

To estimate admission chances, collect:
1. College name (if not mentioned)
2. GPA
3. SAT/ACT score (or if not submitting)
4. Extracurriculars
5. Intended major

LOOK THROUGH MEMORY TO AVOID BEING REDUNDANT IN ASKING QUESTIONS.

If they ask other questions about college admissions, answer clearly. try to be concise. GIVE THEM A PERCENTAGE ON HOW LIKELY THE USER WILL GET IN
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
