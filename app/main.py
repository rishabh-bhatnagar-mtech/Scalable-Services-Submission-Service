import os
import uuid
from confluent_kafka import Producer
from dotenv import load_dotenv
from flask import Flask, request, jsonify

load_dotenv()

app = Flask(__name__)

conf = {
    'bootstrap.servers': os.getenv("KAFKA_BROKERS"),
    'client.id': 'submission-service'
}
producer = Producer(conf)


@app.route('/submissions', methods=['POST'])
def create_submission():
    data = request.json
    submission_id = str(uuid.uuid4())

    required_fields = ['user_id', 'problem_id', 'code', 'language']
    if not all(field in data for field in required_fields):
        return jsonify({"error": f"Missing required fields ({required_fields})"}), 400

    message = {
        "submission_id": submission_id,
        **data
    }

    producer.produce(
        topic=os.getenv("SUBMISSION_TOPIC"),
        key=submission_id,
        value=str(message).encode('utf-8')
    )
    producer.flush()

    return jsonify({
        "submission_id": submission_id,
        "status": "queued"
    }), 202


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
