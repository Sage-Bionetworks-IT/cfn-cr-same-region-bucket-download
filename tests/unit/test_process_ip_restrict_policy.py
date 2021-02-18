import restrict_download_region.restrict_region as restrict_region
import json
import pytest
import boto3
from pytest_mock import MockerFixture
from botocore.stub import Stubber


@pytest.fixture
def bucket_name():
    return "foobar"


@pytest.fixture
def region():
    return "us-east-1"


# a policy unrelated to this Lambda function
@pytest.fixture
def other_policy(bucket_name):
    return{
        "Sid": "AddCannedAcl",
        "Effect": "Allow",
        "Principal": {"AWS": ["arn:aws:iam::111122223333:root", "arn:aws:iam::444455556666:root"]},
        "Action": ["s3:PutObject", "s3:PutObjectAcl"],
        "Resource": "arn:aws:s3:::"+bucket_name+"/*",
        "Condition": {"StringEquals": {"s3:x-amz-acl": ["public-read"]}}
    }


@pytest.fixture
def only_other_policy(other_policy):
    return {
        "Version": "2012-10-17",
        "Statement": [
            other_policy
        ]
    }


@pytest.fixture
def old_ip_policy_with_other_policy(bucket_name, other_policy):
    old_ip_policy = {
        "Sid": "DenyGetObjectForNonMatchingIp",
        "Effect": "Deny",
        "Principal": '*',
        "Action": 's3:GetObject',
        "Resource": 'arn:aws:s3:::'+bucket_name+'/*',
        "Condition": {'NotIpAddress': {'aws:SourceIp': ['52.93.153.170/32',
                                                        '2a05:d07a:c000::/40']},
                      'Null': {'aws:sourceVpc': 'true'}}
    }
    return {
        "Version": "2012-10-17",
        "Statement": [other_policy, old_ip_policy]
    }


@pytest.fixture
def no_policy_statements():
    return {
        "Version": "2012-10-17",
        "Statement": []
    }


@pytest.fixture
def generated_ip_restrict_policy(bucket_name):
    return {
        "Sid": "DenyGetObjectForNonMatchingIp",
        "Effect": "Deny",
        "Principal": '*',
        "Action": 's3:GetObject',
        "Resource": 'arn:aws:s3:::'+bucket_name+'/*',
        "Condition": {'NotIpAddress': {'aws:SourceIp': ['15.230.56.104/31',
                                                        '2600:1f19:8000::/36']},
                      'Null': {'aws:sourceVpc': 'true'}}
    }


@pytest.mark.parametrize("custom_resource_type", [None, 'Create', 'Update'])
def test_process_ip_restrict_policy__has_only_other_statements__event_is_sns_or_create_or_update(mocker: MockerFixture, generated_ip_restrict_policy, bucket_name, region, custom_resource_type, only_other_policy):
    mock_generate_ip_address_policy = mocker.patch.object(
        restrict_region, "generate_ip_address_policy", return_value=generated_ip_restrict_policy, autospec=True)

    # function under test
    restrict_region.process_ip_restrict_policy(
        bucket_name, region, custom_resource_type, only_other_policy)

    # veify that it has been modified with a newly added DenyGetObjectForNonMatchingIp policy
    assert only_other_policy == {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AddCannedAcl",
                "Effect": "Allow",
                "Principal": {"AWS": ["arn:aws:iam::111122223333:root", "arn:aws:iam::444455556666:root"]},
                "Action":["s3:PutObject", "s3:PutObjectAcl"],
                "Resource":"arn:aws:s3:::"+bucket_name+"/*",
                "Condition":{"StringEquals": {"s3:x-amz-acl": ["public-read"]}}
            },
            {
                "Sid": "DenyGetObjectForNonMatchingIp",
                "Effect": "Deny",
                "Principal": '*',
                "Action": 's3:GetObject',
                "Resource": 'arn:aws:s3:::'+bucket_name+'/*',
                "Condition": {'NotIpAddress': {'aws:SourceIp': ['15.230.56.104/31',
                                                                '2600:1f19:8000::/36']},
                              'Null': {'aws:sourceVpc': 'true'}}
            }
        ]
    }

    mock_generate_ip_address_policy.assert_called_once_with(bucket_name, region)


def test_process_ip_restrict_policy__has_only_other_statements__event_is_delete(mocker: MockerFixture, generated_ip_restrict_policy, bucket_name, region, only_other_policy):
    mock_generate_ip_address_policy = mocker.patch.object(
        restrict_region, "generate_ip_address_policy", return_value=generated_ip_restrict_policy, autospec=True)

    custom_resource_type = "Delete"
    # function under test
    restrict_region.process_ip_restrict_policy(
        bucket_name, region, custom_resource_type, only_other_policy)

    # veify that nothing was touched
    assert only_other_policy == {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AddCannedAcl",
                "Effect": "Allow",
                "Principal": {"AWS": ["arn:aws:iam::111122223333:root", "arn:aws:iam::444455556666:root"]},
                "Action":["s3:PutObject", "s3:PutObjectAcl"],
                "Resource":"arn:aws:s3:::"+bucket_name+"/*",
                "Condition":{"StringEquals": {"s3:x-amz-acl": ["public-read"]}}
            }
        ]
    }

    assert not mock_generate_ip_address_policy.called


@pytest.mark.parametrize("custom_resource_type", [None, 'Create', 'Update'])
def test_process_ip_restrict_policy__has_old_ip_policy_with_other_statements__event_is_sns_or_create_or_update(mocker: MockerFixture, generated_ip_restrict_policy, bucket_name, region, custom_resource_type, old_ip_policy_with_other_policy):
    mock_generate_ip_address_policy = mocker.patch.object(
        restrict_region, "generate_ip_address_policy", return_value=generated_ip_restrict_policy, autospec=True)

    # function under test
    restrict_region.process_ip_restrict_policy(
        bucket_name, region, custom_resource_type, old_ip_policy_with_other_policy)

    # veify that it has been modified with an updated policy
    assert old_ip_policy_with_other_policy == {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AddCannedAcl",
                "Effect": "Allow",
                "Principal": {"AWS": ["arn:aws:iam::111122223333:root", "arn:aws:iam::444455556666:root"]},
                "Action":["s3:PutObject", "s3:PutObjectAcl"],
                "Resource":"arn:aws:s3:::"+bucket_name+"/*",
                "Condition":{"StringEquals": {"s3:x-amz-acl": ["public-read"]}}
            },
            {
                "Sid": "DenyGetObjectForNonMatchingIp",
                "Effect": "Deny",
                "Principal": '*',
                "Action": 's3:GetObject',
                "Resource": 'arn:aws:s3:::'+bucket_name+'/*',
                "Condition": {'NotIpAddress': {'aws:SourceIp': ['15.230.56.104/31',
                                                                '2600:1f19:8000::/36']},
                              'Null': {'aws:sourceVpc': 'true'}}
            }
        ]
    }

    mock_generate_ip_address_policy.assert_called_once_with(bucket_name, region)


def test_process_ip_restrict_policy__has_old_ip_policy_with_other_statements__event_is_delete(mocker: MockerFixture, generated_ip_restrict_policy, bucket_name, region, old_ip_policy_with_other_policy):
    mock_generate_ip_address_policy = mocker.patch.object(
        restrict_region, "generate_ip_address_policy", return_value=generated_ip_restrict_policy, autospec=True)

    custom_resource_type = 'Delete'
    # function under test
    restrict_region.process_ip_restrict_policy(
        bucket_name, region, custom_resource_type, old_ip_policy_with_other_policy)

    # veify that the "DenyGetObjectForNonMatchingIp" policy was deleted
    assert old_ip_policy_with_other_policy == {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AddCannedAcl",
                "Effect": "Allow",
                "Principal": {"AWS": ["arn:aws:iam::111122223333:root", "arn:aws:iam::444455556666:root"]},
                "Action":["s3:PutObject", "s3:PutObjectAcl"],
                "Resource":"arn:aws:s3:::"+bucket_name+"/*",
                "Condition":{"StringEquals": {"s3:x-amz-acl": ["public-read"]}}
            }
        ]
    }

    assert not mock_generate_ip_address_policy.called


@pytest.mark.parametrize("custom_resource_type", [None, 'Create', 'Update'])
def test_process_ip_restrict_policy__does_not_have_any_statements__event_is_sns_or_create_or_update(mocker: MockerFixture, generated_ip_restrict_policy, bucket_name, region, custom_resource_type, no_policy_statements):
    mock_generate_ip_address_policy = mocker.patch.object(
        restrict_region, "generate_ip_address_policy", return_value=generated_ip_restrict_policy, autospec=True)

    # function under test
    restrict_region.process_ip_restrict_policy(
        bucket_name, region, custom_resource_type, no_policy_statements)

    # veify that it has been modified with a newly added DenyGetObjectForNonMatchingIp policy
    assert no_policy_statements == {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "DenyGetObjectForNonMatchingIp",
                "Effect": "Deny",
                "Principal": '*',
                "Action": 's3:GetObject',
                "Resource": 'arn:aws:s3:::'+bucket_name+'/*',
                "Condition": {'NotIpAddress': {'aws:SourceIp': ['15.230.56.104/31',
                                                                '2600:1f19:8000::/36']},
                              'Null': {'aws:sourceVpc': 'true'}}
            }
        ]
    }

    mock_generate_ip_address_policy.assert_called_once_with(bucket_name, region)


def test_process_ip_restrict_policy__does_not_have_any_statements__event_is_delete(mocker: MockerFixture, generated_ip_restrict_policy, bucket_name, region, no_policy_statements):
    mock_generate_ip_address_policy = mocker.patch.object(
        restrict_region, "generate_ip_address_policy", return_value=generated_ip_restrict_policy, autospec=True)

    custom_resource_type = "Delete"
    # function under test
    restrict_region.process_ip_restrict_policy(
        bucket_name, region, custom_resource_type, no_policy_statements)

    # veify that nothing was touched
    assert no_policy_statements == {
        "Version": "2012-10-17",
        "Statement": []
    }

    assert not mock_generate_ip_address_policy.called
