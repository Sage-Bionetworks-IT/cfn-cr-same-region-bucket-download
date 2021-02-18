import restrict_download_region.restrict_region as restrict_region
import json
import pytest
import boto3
from pytest_mock import MockerFixture
from botocore.stub import Stubber


@pytest.fixture
def create_event():
    return {
        "RequestType": "Create",
        "ResponseURL": "pre-signed-url-for-create-response"
    }


@pytest.fixture
def sns_event():
    return {
        "Records": [
            {
                "EventVersion": "1.0",
                "EventSubscriptionArn": "arn:aws:sns:us-east-2:123456789012:sns-lambda:21be56ed-a058-49f5-8c98-aedd2564c486",
                "EventSource": "aws:sns",
                # we don't actually care what's in the sns message
                "Sns": {}
            }
        ]
    }


@pytest.fixture
def context():
    # we don't care what's in this object
    return {}


def test_handler__REGION_not_set(mocker: MockerFixture, create_event, context):
    mocker.patch.object(restrict_region, "REGION", None)
    mocker.patch.object(restrict_region, "BUCKET_NAME", "my-bucket-name")

    with pytest.raises(ValueError):
        restrict_region.handler(create_event, context)


def test_handler__BUCKET_NAME_not_set(mocker: MockerFixture, create_event, context):
    mocker.patch.object(restrict_region, "REGION", "us-east-1")
    mocker.patch.object(restrict_region, "BUCKET_NAME", None)

    with pytest.raises(ValueError):
        restrict_region.handler(create_event, context)


def test_handler__cfn_event(mocker: MockerFixture, create_event, context):
    region = "us-east-1"
    bucket_name = "my-bucket-name"

    mocker.patch.object(restrict_region, "REGION", region)
    mocker.patch.object(restrict_region, "BUCKET_NAME", bucket_name)

    bucket_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "id": "foobar"
            }
        ]
    }

    mock_s3 = mocker.MagicMock(boto3.client('s3'))
    mocker.patch.object(boto3, "client", autospec=True).return_value = mock_s3

    mock_handle_custom_resource_message = mocker.patch.object(
        restrict_region, "handle_custom_resource_message", autospec=True)
    mock_get_bucket_policy = mocker.patch.object(
        restrict_region, "get_bucket_policy", return_value=bucket_policy, autospec=True)
    mock_process_ip_restrict_policy = mocker.patch.object(restrict_region, "process_ip_restrict_policy", autospec=True)
    mock_update_bucket_policy = mocker.patch.object(restrict_region, "update_bucket_policy", autospec=True)

    # function under test
    restrict_region.handler(create_event, context)

    mock_handle_custom_resource_message.assert_called_once_with(create_event, context)
    mock_get_bucket_policy.assert_called_once_with(mock_s3, bucket_name)
    mock_process_ip_restrict_policy.assert_called_once_with(bucket_name, region, bucket_policy, "Create")
    mock_update_bucket_policy.assert_called_once_with(mock_s3, bucket_name, bucket_policy)


def test_handler__cfn_event(mocker: MockerFixture, sns_event, context):
    region = "us-east-1"
    bucket_name = "my-bucket-name"

    mocker.patch.object(restrict_region, "REGION", region)
    mocker.patch.object(restrict_region, "BUCKET_NAME", bucket_name)

    bucket_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "id": "foobar"
            }
        ]
    }

    mock_s3 = mocker.MagicMock(boto3.client('s3'))
    mocker.patch.object(boto3, "client", autospec=True).return_value = mock_s3

    mock_handle_custom_resource_message = mocker.patch.object(
        restrict_region, "handle_custom_resource_message", autospec=True)
    mock_get_bucket_policy = mocker.patch.object(
        restrict_region, "get_bucket_policy", return_value=bucket_policy, autospec=True)
    mock_process_ip_restrict_policy = mocker.patch.object(restrict_region, "process_ip_restrict_policy", autospec=True)
    mock_update_bucket_policy = mocker.patch.object(restrict_region, "update_bucket_policy", autospec=True)

    # function under test
    restrict_region.handler(sns_event, context)

    mock_handle_custom_resource_message.assert_called_once_with(sns_event, context)
    mock_get_bucket_policy.assert_called_once_with(mock_s3, bucket_name)
    mock_process_ip_restrict_policy.assert_called_once_with(bucket_name, region, None, bucket_policy)
    mock_update_bucket_policy.assert_called_once_with(mock_s3, bucket_name, bucket_policy)
