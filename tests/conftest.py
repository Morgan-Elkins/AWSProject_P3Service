import os

import boto3
import pytest
from moto import mock_aws

os.environ['AWS_REGION'] = 'eu-west-2'
os.environ['AWS_Q3'] = 'testing'
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
os.environ['SENDER_EMAIL'] = 'testing'
os.environ['RECIPIENT_EMAIL'] = 'testing'

from app import send_email, app

@pytest.fixture(scope='function')
def client():
    with mock_aws():
        sqs = boto3.client('sqs', region_name='eu-west-2')

        queue_url = sqs.create_queue(
            QueueName='testing'
        )['QueueUrl']

        yield sqs


def test_get_health(client):
    response = app.test_client().get("/health")
    assert b'{"status":"Healthy"}\n' in response.data

# def test_sending_email(client):
#     data = {"title": "pytest", "desc": "pytest desc", "prio": 0}
#     response = send_email(data)
#     assert response == "Email sent!"