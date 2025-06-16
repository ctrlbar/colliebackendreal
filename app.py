import os
import openai
from flask import Flask, request, jsonify
from openai.error import RateLimitError, OpenAIError

app = Flask(__name__)

openai.api_key = os.getenv("OPENAI_API_KEY")

@app.route("/api", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        prompt = data.get("prompt", "")

        if not openai.api_key:
            return jsonify({"error": "API key not configured"}), 500

        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert college advisor."},
                {"role": "user", "content": prompt}
            ],
        )
        answer = response.choices[0].message.content.strip()

        return jsonify({"answer": answer})

    except RateLimitError:
        return jsonify({"error": "OpenAI API quota exceeded. Please try again later."}), 429
    except OpenAIError as e:
        # Handle other OpenAI API errors here
        return jsonify({"error": f"OpenAI API error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run()
