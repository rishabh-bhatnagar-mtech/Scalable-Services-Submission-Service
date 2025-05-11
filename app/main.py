import json
import os
import uuid

from confluent_kafka import Producer
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
log = app.logger

db_config = (
    f"postgresql+psycopg://{os.getenv('DB_USERNAME')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME')}"
)

app.config['SQLALCHEMY_DATABASE_URI'] = (
    f"postgresql+psycopg://{os.getenv('DB_USERNAME')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME')}"
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


class Submission(db.Model):
    __tablename__ = 'submissions'
    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.String(64), nullable=False)
    problem_id = db.Column(db.String(64), nullable=False)
    code = db.Column(db.Text, nullable=False)
    language = db.Column(db.String(32), nullable=False)
    status = db.Column(db.String(32), default="queued")
    result = db.Column(db.JSON, nullable=True)


# ---- Kafka Config ----
conf_producer = {
    'bootstrap.servers': os.getenv("KAFKA_BROKERS"),
    'client.id': 'submission-service-producer'
}
producer = Producer(conf_producer)

SUBMISSION_TOPIC = os.getenv("SUBMISSION_TOPIC")


@app.route('/submissions', methods=['POST'])
def create_submission():
    data = request.json
    submission_id = str(uuid.uuid4())

    required_fields = ['user_id', 'problem_id', 'code', 'language']
    if not all(field in data for field in required_fields):
        return jsonify({"error": f"Missing required fields ({required_fields})"}), 400

    # Store in DB with status 'queued'
    submission = Submission(
        id=submission_id,
        user_id=data['user_id'],
        problem_id=data['problem_id'],
        code=data['code'],
        language=data['language'],
        status="queued"
    )
    db.session.add(submission)
    db.session.commit()

    message = {
        "submission_id": submission_id,
        **data
    }

    log.info(f"Adding a submission in {SUBMISSION_TOPIC}")
    producer.produce(
        topic=SUBMISSION_TOPIC,
        key=submission_id,
        value=json.dumps(message).encode('utf-8')
    )
    producer.flush()

    return jsonify({
        "submission_id": submission_id,
        "status": "queued"
    }), 202


@app.route('/submissions/<submission_id>/result', methods=['GET'])
def get_submission_result(submission_id):
    submission = Submission.query.get(submission_id)
    if submission is None:
        return jsonify({"error": "Submission not found"}), 404

    if submission.status != "completed":
        return jsonify({"status": submission.status, "result": None}), 202

    return jsonify({
        "submission_id": submission.id,
        "status": submission.status,
        "result": submission.result
    }), 200


if __name__ == '__main__':
    # Create tables if not exist
    with app.app_context():
        db.create_all()

    app.run(host='0.0.0.0', port=5000)
