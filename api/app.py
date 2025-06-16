from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/", methods=["GET"])
def index():
    return "API is running!"

@app.route("/", methods=["POST"])
def handler():
    data = request.json
    prompt = data.get("prompt", "")
    return jsonify({"received_prompt": prompt})

if __name__ == "__main__":
    app.run()
