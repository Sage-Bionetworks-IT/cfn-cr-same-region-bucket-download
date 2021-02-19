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
def region_ip_prefixes():
    return ["3.5.140.0/22", "52.94.6.0/24"]


@pytest.fixture
def context():
    # we don't care what's in this object
    return {}


@pytest.mark.parametrize("cfn_request_type", ["Create", "Update"])
def test_handler__cfn_create_and_update_events(mocker: MockerFixture, cfn_request_type, context, bucket_policy, region_ip_prefixes):

    cfn_event = {
        "RequestType": cfn_request_type,
        "ResponseURL": "pre-signed-url-for-create-response"
    }

    bucket_name = "my-bucket-name"
    region = "us-east-1"
    mocker.patch.object(restrict_region, "REGION", region)

    mock_s3 = mocker.MagicMock(boto3.client('s3'))
    mocker.patch.object(boto3, "client", autospec=True).return_value = mock_s3

    mock_handle_custom_resource_message = mocker.patch.object(
        restrict_region, "handle_custom_resource_status_message", autospec=True)
    mock_handle_custom_resource_message.return_value.__enter__.return_value = cfn_event.get('RequestType')

    mock_get_bucket_name_from_custom_resouce = mocker.patch.object(
        restrict_region, "get_bucket_name_from_custom_resouce", return_value=bucket_name, autospec=True)
    mock_get_all_region_restricted_bucket_names = mocker.patch.object(
        restrict_region, "get_all_region_restricted_bucket_names", autospec=True)
    mock_get_ip_prefixes_for_region = mocker.patch.object(
        restrict_region, "get_ip_prefixes_for_region", return_value=region_ip_prefixes, autospec=True)

    mock_get_bucket_policy = mocker.patch.object(
        restrict_region, "get_bucket_policy", return_value=bucket_policy, autospec=True)
    mock_process_ip_restrict_policy = mocker.patch.object(restrict_region, "process_ip_restrict_policy", autospec=True)
    mock_update_bucket_policy = mocker.patch.object(restrict_region, "update_bucket_policy", autospec=True)

    # function under test
    restrict_region.handler(cfn_event, context)

    assert not mock_get_all_region_restricted_bucket_names.called
    mock_get_bucket_name_from_custom_resouce.assert_called_once_with(cfn_event)

    mock_get_ip_prefixes_for_region.assert_called_once_with()

    mock_handle_custom_resource_message.assert_called_once_with(cfn_event, context)
    mock_get_bucket_policy.assert_called_once_with(mock_s3, bucket_name)
    mock_process_ip_restrict_policy.assert_called_once_with(
        bucket_name, region_ip_prefixes, cfn_request_type, bucket_policy)
    mock_update_bucket_policy.assert_called_once_with(mock_s3, bucket_name, bucket_policy)


def test_handler__cfn_delete_event(mocker: MockerFixture, context, bucket_policy):
    delete_event = {
        "RequestType": "Delete",
        "ResponseURL": "pre-signed-url-for-create-response"
    }

    bucket_name = "my-bucket-name"
    region = "us-east-1"
    mocker.patch.object(restrict_region, "REGION", region)

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
    mock_handle_custom_resource_message.return_value.__enter__.return_value = delete_event.get('RequestType')

    mock_get_bucket_name_from_custom_resouce = mocker.patch.object(
        restrict_region, "get_bucket_name_from_custom_resouce", return_value=bucket_name, autospec=True)
    mock_get_all_region_restricted_bucket_names = mocker.patch.object(
        restrict_region, "get_all_region_restricted_bucket_names", autospec=True)
    mock_get_ip_prefixes_for_region = mocker.patch.object(
        restrict_region, "get_ip_prefixes_for_region", autospec=True)

    mock_get_bucket_policy = mocker.patch.object(
        restrict_region, "get_bucket_policy", return_value=bucket_policy, autospec=True)
    mock_process_ip_restrict_policy = mocker.patch.object(restrict_region, "process_ip_restrict_policy", autospec=True)
    mock_update_bucket_policy = mocker.patch.object(restrict_region, "update_bucket_policy", autospec=True)

    # function under test
    restrict_region.handler(delete_event, context)

    assert not mock_get_all_region_restricted_bucket_names.called
    mock_get_bucket_name_from_custom_resouce.assert_called_once_with(delete_event)

    assert not mock_get_ip_prefixes_for_region.called

    mock_handle_custom_resource_message.assert_called_once_with(delete_event, context)
    mock_get_bucket_policy.assert_called_once_with(mock_s3, bucket_name)
    mock_process_ip_restrict_policy.assert_called_once_with(
        bucket_name, None, "Delete", bucket_policy)
    mock_update_bucket_policy.assert_called_once_with(mock_s3, bucket_name, bucket_policy)


def test_handler__sns_event(mocker: MockerFixture, context, bucket_policy, region_ip_prefixes):

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
    mocker.patch.object(restrict_region, "REGION", region)

    bucket_names = ["foo-bucket", "bar-bucket"]

    mock_s3 = mocker.MagicMock(boto3.client('s3'))
    mocker.patch.object(boto3, "client", autospec=True).return_value = mock_s3

    mock_get_bucket_name_from_custom_resouce = mocker.patch.object(
        restrict_region, "get_bucket_name_from_custom_resouce", autospec=True)
    mock_get_all_region_restricted_bucket_names = mocker.patch.object(
        restrict_region, "get_all_region_restricted_bucket_names", return_value=bucket_names, autospec=True)
    mock_get_ip_prefixes_for_region = mocker.patch.object(
        restrict_region, "get_ip_prefixes_for_region", return_value=region_ip_prefixes, autospec=True)

    mock_handle_custom_resource_message = mocker.patch.object(
        restrict_region, "handle_custom_resource_status_message", autospec=True)
    mock_handle_custom_resource_message.return_value.__enter__.return_value = sns_event.get('RequestType')

    mock_get_bucket_policy = mocker.patch.object(
        restrict_region, "get_bucket_policy", return_value=bucket_policy, autospec=True)
    mock_process_ip_restrict_policy = mocker.patch.object(restrict_region, "process_ip_restrict_policy", autospec=True)
    mock_update_bucket_policy = mocker.patch.object(restrict_region, "update_bucket_policy", autospec=True)

    # function under test
    restrict_region.handler(sns_event, context)

    mock_handle_custom_resource_message.assert_called_once_with(sns_event, context)

    assert not mock_get_bucket_name_from_custom_resouce.called
    mock_get_all_region_restricted_bucket_names.assert_called_once_with()
    mock_get_ip_prefixes_for_region.assert_called_once_with()

    # there should be 2 calls for each function since we found 2 buckets
    assert mock_get_bucket_policy.call_args_list == [
        mocker.call(mock_s3, bucket_names[0]),
        mocker.call(mock_s3, bucket_names[1])]
    assert mock_process_ip_restrict_policy.call_args_list == [
        mocker.call(bucket_names[0], region_ip_prefixes, None, bucket_policy),
        mocker.call(bucket_names[1], region_ip_prefixes, None, bucket_policy)]
    mock_update_bucket_policy.call_args_list == [
        mocker.call(mock_s3, bucket_names[0], bucket_policy),
        mocker.call(mock_s3, bucket_names[1], bucket_policy)]
