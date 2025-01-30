import json
import os
import threading
import time

from botocore.exceptions import ClientError
from dotenv import load_dotenv
import boto3
from flask import Flask

load_dotenv()

AWS_REGION = os.getenv("AWS_REGION")
AWS_QUEUE = os.getenv("AWS_Q3")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL")

sqs = boto3.client('sqs', region_name=AWS_REGION)
client = boto3.client('ses',region_name=AWS_REGION)

def send_email(json_body):
    # The subject line for the email.
    SUBJECT = f"{json_body.get("title")}"

    # The email body for recipients with non-HTML email clients.
    BODY_TEXT = (f"{json_body.get("title")}\r\n"
                 f"{json_body.get("desc")}"
                 )

    # The HTML body of the email.
    BODY_HTML = f"""<html>
    <head></head>
    <body>
      <h1>{json_body.get("title")}</h1>
      <p>{json_body.get("desc")}</p>
    </body>
    </html>
                """

    # The character encoding for the email.
    CHARSET = "UTF-8"

    # Try to send the email.
    try:
        # Provide the contents of the email.
        response = client.send_email(
            Destination={
                'ToAddresses': [
                    RECIPIENT_EMAIL,
                ],
            },
            Message={
                'Body': {
                    'Html': {
                        'Charset': CHARSET,
                        'Data': BODY_HTML,
                    },
                    'Text': {
                        'Charset': CHARSET,
                        'Data': BODY_TEXT,
                    },
                },
                'Subject': {
                    'Charset': CHARSET,
                    'Data': SUBJECT,
                },
            },
            Source=SENDER_EMAIL,
        )
    # Display an error if something goes wrong.
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        print("Email sent! Message ID:"),
        print(response['MessageId'])

def create_app():
    app = Flask(__name__)

    # http://localhost:5003/health
    @app.route("/health", methods=["GET"])
    def home():
        print(f"{AWS_REGION} {AWS_QUEUE}")
        return "Healthy", 200

    return app

def get_messages():
    while True:
        try:
            response = sqs.receive_message(
                QueueUrl=AWS_QUEUE,
                AttributeNames=[
                    'SentTimestamp'
                ],
                MaxNumberOfMessages=1,
                MessageAttributeNames=[
                    'All'
                ],
                VisibilityTimeout=0,
                WaitTimeSeconds=0
            )

            message = response['Messages'][0]
            receipt_handle = message['ReceiptHandle']

            # Delete received message from queue
            sqs.delete_message(
                QueueUrl=AWS_QUEUE,
                ReceiptHandle=receipt_handle
            )

            body = message['Body']
            body = body.replace("\'", "\"") # WHY?????
            json_body = json.loads(body)
            print(f"Message contents {json_body}")

            send_email(json_body)

        except:
            pass
        time.sleep(1)


if __name__ == '__main__':
    app = create_app()
    threading.Thread(target=lambda: app.run(port=5003)).start()
    threading.Thread(target=lambda: get_messages()).start()