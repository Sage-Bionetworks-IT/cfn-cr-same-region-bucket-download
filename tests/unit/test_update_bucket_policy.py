import restrict_download_region.restrict_region as restrict_region
import boto3
import json
import pytest
import botocore
from pytest_mock import MockerFixture


def test_get_bucket_policy__has_statement(mocker: MockerFixture):
    mock_s3 = mocker.MagicMock(spec=boto3.client('s3'))

    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AddCannedAcl",
                "Effect": "Allow",
                "Principal": {"AWS": ["arn:aws:iam::111122223333:root", "arn:aws:iam::444455556666:root"]},
                "Action":["s3:PutObject", "s3:PutObjectAcl"],
                "Resource":"arn:aws:s3:::DOC-EXAMPLE-BUCKET/*",
                "Condition":{"StringEquals": {"s3:x-amz-acl": ["public-read"]}}
            }
        ]
    }

    # function under test
    restrict_region.update_bucket_policy(mock_s3, "foobar", policy)

    mock_s3.put_bucket_policy.assert_called_once_with(Bucket="foobar", Policy=json.dumps(policy))
    assert not mock_s3.delete_bucket_policy.called


def test_update_bucket_policy__no_statements(mocker: MockerFixture):
    mock_s3 = mocker.MagicMock(spec=boto3.client('s3'))

    policy = {
        "Version": "2012-10-17",
        "Statement": []
    }

    # function under test
    restrict_region.update_bucket_policy(mock_s3, "foobar", policy)

    mock_s3.delete_bucket_policy.assert_called_once_with(Bucket="foobar")
    assert not mock_s3.put_bucket_policy.called
