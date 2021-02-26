import restrict_download_region.restrict_region as restrict_region
import json
import pytest
import boto3
from pytest_mock import MockerFixture
from botocore.stub import Stubber


@pytest.fixture
def bucket_policy():
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "id": "foobar"
            }
        ]
    }


@pytest.fixture
def context():
    # we don't care what's in this object
    return {}


@pytest.mark.parametrize("cfn_request_type", ["Create", "Update"])
def test_handler__cfn_create_and_update_events(mocker: MockerFixture,
                                               cfn_request_type,
                                               context,
                                               bucket_policy):

    cfn_event = {
        "RequestType": cfn_request_type,
        "ResponseURL": "pre-signed-url-for-create-response"
    }

    bucket_name = "my-bucket-name"
    region = "us-east-1"
    mocker.patch.object(restrict_region, "AWS_REGION", region)
    mocker.patch.object(restrict_region, "BUCKET_NAME", bucket_name)

    mock_s3 = mocker.MagicMock(boto3.client('s3'))
    mocker.patch.object(boto3, "client", autospec=True).return_value = mock_s3

    mock_handle_custom_resource_message = mocker.patch.object(
        restrict_region, "handle_custom_resource_status_message", autospec=True)
    mock_handle_custom_resource_message.return_value.__enter__.return_value = cfn_event.get(
        'RequestType')

    mock_get_bucket_policy = mocker.patch.object(
        restrict_region, "get_bucket_policy", return_value=bucket_policy, autospec=True)
    mock_process_ip_restrict_policy = mocker.patch.object(
        restrict_region, "process_ip_restrict_policy", autospec=True)
    mock_update_bucket_policy = mocker.patch.object(
        restrict_region, "update_bucket_policy", autospec=True)

    # function under test
    restrict_region.handler(cfn_event, context)

    mock_handle_custom_resource_message.assert_called_once_with(cfn_event, context)
    mock_get_bucket_policy.assert_called_once_with(mock_s3, bucket_name)
    mock_process_ip_restrict_policy.assert_called_once_with(
        bucket_name, cfn_request_type, bucket_policy)
    mock_update_bucket_policy.assert_called_once_with(mock_s3, bucket_name, bucket_policy)


def test_handler__cfn_delete_event(mocker: MockerFixture, context, bucket_policy):
    delete_event = {
        "RequestType": "Delete",
        "ResponseURL": "pre-signed-url-for-create-response"
    }

    bucket_name = "my-bucket-name"
    region = "us-east-1"
    mocker.patch.object(restrict_region, "AWS_REGION", region)
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
        restrict_region, "handle_custom_resource_status_message", autospec=True)
    mock_handle_custom_resource_message.return_value.__enter__.return_value = delete_event.get(
        'RequestType')

    mock_get_bucket_policy = mocker.patch.object(
        restrict_region, "get_bucket_policy", return_value=bucket_policy, autospec=True)
    mock_process_ip_restrict_policy = mocker.patch.object(
        restrict_region, "process_ip_restrict_policy", autospec=True)
    mock_update_bucket_policy = mocker.patch.object(
        restrict_region, "update_bucket_policy", autospec=True)

    # function under test
    restrict_region.handler(delete_event, context)

    mock_handle_custom_resource_message.assert_called_once_with(delete_event, context)
    mock_get_bucket_policy.assert_called_once_with(mock_s3, bucket_name)
    mock_process_ip_restrict_policy.assert_called_once_with(
        bucket_name, "Delete", bucket_policy)
    mock_update_bucket_policy.assert_called_once_with(mock_s3, bucket_name, bucket_policy)


def test_handler__sns_event(mocker: MockerFixture, context, bucket_policy):

    sns_event = {
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

    region = "us-east-1"
    bucket_name = "my-bucket-name"
    mocker.patch.object(restrict_region, "AWS_REGION", region)
    mocker.patch.object(restrict_region, "BUCKET_NAME", bucket_name)

    mock_s3 = mocker.MagicMock(boto3.client('s3'))
    mocker.patch.object(boto3, "client", autospec=True).return_value = mock_s3

    mock_handle_custom_resource_message = mocker.patch.object(
        restrict_region, "handle_custom_resource_status_message", autospec=True)
    mock_handle_custom_resource_message.return_value.__enter__.return_value = sns_event.get(
        'RequestType')

    mock_get_bucket_policy = mocker.patch.object(
        restrict_region, "get_bucket_policy", return_value=bucket_policy, autospec=True)
    mock_process_ip_restrict_policy = mocker.patch.object(
        restrict_region, "process_ip_restrict_policy", autospec=True)
    mock_update_bucket_policy = mocker.patch.object(
        restrict_region, "update_bucket_policy", autospec=True)

    # function under test
    restrict_region.handler(sns_event, context)

    mock_handle_custom_resource_message.assert_called_once_with(sns_event, context)

    # there should be 2 calls for each function since we found 2 buckets
    mock_get_bucket_policy.assert_called_once_with(mock_s3, bucket_name)
    mock_process_ip_restrict_policy.assert_called_once_with(
        bucket_name, None, bucket_policy)
    mock_update_bucket_policy.assert_called_once_with(mock_s3, bucket_name, bucket_policy)
