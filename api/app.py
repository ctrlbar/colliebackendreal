# api/index.py
import os
import openai

def handler(request):
    try:
        request_body = request.get_json()
        prompt = request_body.get("prompt", "")

        openai.api_key = os.environ.get("OPENAI_API_KEY")
        if not openai.api_key:
            return {
                "statusCode": 500,
                "body": "OpenAI API key not set."
            }

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert college advisor..."},
                {"role": "user", "content": prompt}
            ]
        )

        answer = response.choices[0].message.content.strip()

        return {
            "statusCode": 200,
            "headers": { "Content-Type": "application/json" },
            "body": answer
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "body": str(e)
        }
