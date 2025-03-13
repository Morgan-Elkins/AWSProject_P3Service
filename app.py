import json
import os
import threading
import time

from botocore.exceptions import ClientError
from dotenv import load_dotenv
import boto3
from flask import Flask, jsonify

from botocore.exceptions import ClientError
import markdown

load_dotenv()

AWS_REGION = os.getenv("AWS_REGION")
AWS_QUEUE = os.getenv("AWS_Q3")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL")

sqs = boto3.client('sqs', region_name=AWS_REGION)
client = boto3.client('ses',region_name=AWS_REGION)

app = Flask(__name__)

# Bedrock client

bedrock_client = boto3.client(
    service_name="bedrock-runtime",
    region_name="eu-west-2"
)

model_id = "anthropic.claude-3-sonnet-20240229-v1:0"

def getLLMmessage(userMessage):
    # Start a conversation with the user message.
    user_message = userMessage
    conversation = [
        {
            "role": "user",
            "content": [{"text": user_message}],
        }
    ]

    try:
        # Send the message to the model, using a basic inference configuration.
        response = bedrock_client.converse(
            modelId=model_id,
            messages=conversation,
            inferenceConfig={"maxTokens": 512, "temperature": 0.5, "topP": 0.9},
        )

        # Extract and print the response text.
        response_text = response["output"]["message"]["content"][0]["text"]
        return response_text
    except (ClientError, Exception) as e:
        print(f"ERROR: Can't invoke '{model_id}'. Reason: {e}")
        return ""


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
      <br>
      <p><b>A suggested improvement is </b>: {markdown.markdown(getLLMmessage(str(json_body.get('desc'))))}</p>
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
        return "Email failure"
    else:
        print("Email sent! Message ID:"),
        print(response['MessageId'])
        return "Email sent!"

# http://localhost:5003/health
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status":"Healthy"}), 200

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
                WaitTimeSeconds=2
            )

            message = response['Messages'][0]
            receipt_handle = message['ReceiptHandle']

            # Delete received message from queue
            sqs.delete_message(
                QueueUrl=AWS_QUEUE,
                ReceiptHandle=receipt_handle
            )

            body = message['Body']
            json_body = eval(body)
            print(f"Message contents {json_body}")

            if json_body.get("title") is None or json_body.get("desc") is None or json_body.get("prio") is None:
                continue

            send_email(json_body)

        except:
            pass

def background_thread():
    thread = threading.Thread(target=get_messages, daemon=True)
    thread.start()
    return thread

bg_thread = background_thread()

#Docker: docker run --env-file ./.env -p 8083:8083 --rm p3service-flask-app
if __name__ == '__main__':
    threading.Thread(target=lambda: app.run()).start()
