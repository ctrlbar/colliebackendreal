import os
import openai
import json

openai.api_key = os.getenv("OPENAI_API_KEY")

def handler(request):
    try:
        data = request.get_json()
        prompt = data.get("prompt", "")

        if not openai.api_key:
            return {
                "statusCode": 500,
                "body": json.dumps({"error": "API key not configured"})
            }

        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert college advisor."},
                {"role": "user", "content": prompt}
            ],
        )

        answer = response.choices[0].message.content.strip()

        return {
            "statusCode": 200,
            "body": json.dumps({"answer": answer})
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
