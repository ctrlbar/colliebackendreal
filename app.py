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
                {"role": "system", "content": "You are an expert college advisor. When prompted, ask the student their: GPA, standardized test scores, extracurriculars and intended major. Then, ask them for their preferred colleges. Next, give them an idea of how likely it is to get into their preferred college and what steps can be done to better their likelihood of getting into said college. If student requires other college help, help them."},
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