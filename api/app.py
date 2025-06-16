from flask import Flask, request, jsonify
import os
import openai

app = Flask(__name__)

# Read API key from environment variable (set this in Vercel dashboard)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

@app.route("/", methods=["POST"])
def handler():
    data = request.json
    prompt = data.get("prompt", "")
    
    if not OPENAI_API_KEY:
        return jsonify({"error": "API key not configured"}), 500
    
    openai.api_key = OPENAI_API_KEY
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert college advisor. Ask the student for their stats, standardized test scores, and extracurriculars, and major. Then, try and understand what colleges they want to go to and rate their likelihood of getting into their respective colleges. Adapt to the user's needs as needed."},
                {"role": "user", "content": prompt}
            ]
        )
        answer = response.choices[0].message.content.strip()
        return jsonify({"answer": answer})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run()
