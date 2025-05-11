import json
import logging
import os
import signal
import sys

from confluent_kafka import Consumer, KafkaError
from sqlalchemy import create_engine, Column, String, Text, JSON
from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

RESULTS_TOPIC = os.getenv("RESULTS_TOPIC", "code-results")

conf_consumer = {
    'bootstrap.servers': os.getenv("KAFKA_BROKERS"),
    'group.id': 'submission-service-consumer-group',
    'auto.offset.reset': 'earliest'
}

consumer = Consumer(conf_consumer)

DATABASE_URL = (
    f"postgresql+psycopg://{os.getenv('DB_USERNAME')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME')}"
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = scoped_session(sessionmaker(bind=engine))
Base = declarative_base()


class Submission(Base):
    __tablename__ = 'submissions'

    id = Column(String(36), primary_key=True)
    user_id = Column(String(64), nullable=False)
    problem_id = Column(String(64), nullable=False)
    code = Column(Text, nullable=False)
    language = Column(String(32), nullable=False)
    status = Column(String(32), default="queued")
    result = Column(JSON, nullable=True)


def consume_results():
    consumer.subscribe([RESULTS_TOPIC])
    log.info(f"Subscribed to {RESULTS_TOPIC} topic for results consumption.")

    try:
        while True:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                else:
                    log.error(f"Consumer error: {msg.error()}")
                    continue

            try:
                result_value = msg.value().decode('utf-8')
                result_data = json.loads(result_value)
                submission_id = result_data.get("submission_id")
                if submission_id:
                    session = SessionLocal()
                    submission = session.query(Submission).get(submission_id)
                    if submission:
                        submission.status = "completed"
                        submission.result = result_data
                        session.commit()
                        log.info(f"Updated result for submission_id: {submission_id}")
                    session.close()
            except Exception as e:
                log.error(f"Error processing message: {e}")
    except KeyboardInterrupt:
        log.info("Consumer interrupted by user")
    finally:
        consumer.close()
        SessionLocal.remove()
        log.info("Consumer closed gracefully")


def shutdown_handler(signum, frame):
    log.info("Shutdown signal received, closing consumer...")
    consumer.close()
    SessionLocal.remove()
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)
    consume_results()
