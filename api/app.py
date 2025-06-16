from flask import Flask, request, jsonify
import os, openai

app = Flask(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

@app.route("/", methods=["GET"])
def index():
    return "API is running!"

@app.route("/", methods=["POST"])
def handler():
    data = request.json
    prompt = data.get("prompt", "")
    if not OPENAI_API_KEY:
        return jsonify({"error": "API key not configured"}), 500

    openai.api_key = OPENAI_API_KEY
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are an expert college advisor."},
            {"role": "user", "content": prompt}
        ]
    )
    return jsonify({"answer": response.choices[0].message.content.strip()})
