import restrict_download_region.restrict_region as restrict_region
import boto3
import json
import pytest
import botocore
from pytest_mock import MockerFixture


def test_get_bucket_policy__s3_has_policy(mocker: MockerFixture):
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

    mock_s3.get_bucket_policy.return_value = {"Policy": json.dumps(policy)}

    assert restrict_region.get_bucket_policy(mock_s3, "foobar") == policy
    mock_s3.get_bucket_policy.assert_called_once_with(Bucket="foobar")


def test_get_bucket_policy__s3_no_policy(mocker: MockerFixture):
    mock_s3 = mocker.MagicMock(spec=boto3.client('s3'))

    error_response = {'Error': {'Code': 'NoSuchBucketPolicy',
                                'Message': 'The bucket policy does not exist',
                                'BucketName': 'some-tested-bucket'}
                      }
    mock_s3.get_bucket_policy.side_effect = botocore.exceptions.ClientError(error_response, "GetBucketPolicy")

    assert restrict_region.get_bucket_policy(mock_s3, "foobar") == {
        "Version": "2012-10-17",
        "Statement": []
    }
    mock_s3.get_bucket_policy.assert_called_once_with(Bucket="foobar")


def test_get_bucket_policy__s3_other_exception(mocker: MockerFixture):
    mock_s3 = mocker.MagicMock(spec=boto3.client('s3'))

    error_response = {'Error': {'Code': 'SomeOtherException',
                                'Message': 'you got another exception',
                                'BucketName': 'some-tested-bucket'}
                      }
    mock_s3.get_bucket_policy.side_effect = botocore.exceptions.ClientError(error_response, "GetBucketPolicy")

    with pytest.raises(botocore.exceptions.ClientError):
        restrict_region.get_bucket_policy(mock_s3, "foobar")
    mock_s3.get_bucket_policy.assert_called_once_with(Bucket="foobar")
