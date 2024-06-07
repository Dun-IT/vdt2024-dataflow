import csv
import time
import json
from kafka import KafkaProducer
from kafka.errors import KafkaError

BOOTSTRAP_SERVERS = 'localhost:9092'
TOPIC_NAME = 'vdt2024'
FILE_PATH = 'data/log_action.csv'


def read_and_send_data_to_kafka(file_path):
    producer = KafkaProducer(
        bootstrap_servers=BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    try:
        with open(file_path, mode='r') as file:
            csv_reader = csv.DictReader(file, fieldnames=['student_code', 'activity', 'numberOfFile', 'timestamp'])
            for row in csv_reader:
                message = {
                    'student_code': int(row['student_code']),
                    'activity': row['activity'],
                    'numberOfFile': int(row['numberOfFile']),
                    'timestamp': row['timestamp']
                }
                producer.send(TOPIC_NAME, message)
                try:
                    print(
                        f"Thành công: {message}")
                except KafkaError as e:
                    print(f"Thất bại: {e}")

                time.sleep(1)
    except Exception as e:
        print(f"Error occurred: {e}")
    finally:
        producer.close()


read_and_send_data_to_kafka(FILE_PATH)
