import restrict_download_region.restrict_region as restrict_region
import requests
import json
import pkg_resources
from pytest_mock import MockerFixture


def test_generate_ip_address_policy(mocker: MockerFixture):
    mock_requests_get = mocker.patch.object(requests, "get", autospec=True)
    mock_requests_get.return_value.json.return_value = json.load(
        open(pkg_resources.resource_filename(__name__, 'sample_ip_ranges.json')))

    bucket_name = "mytestbucket"
    # function under test

    assert restrict_region.generate_ip_address_policy(bucket_name, "us-east-1") == {'Action': 's3:GetObject',
                                                                                    'Condition': {'NotIpAddress': {'aws:SourceIp': ['15.230.56.104/31',
                                                                                                                                    '2600:1f19:8000::/36']},
                                                                                                  'Null': {'aws:sourceVpc': 'true'}},
                                                                                    'Effect': 'Deny',
                                                                                    'Principal': '*',
                                                                                    'Resource': 'arn:aws:s3:::'+bucket_name+'/*',
                                                                                    'Sid': 'DenyGetObjectForNonMatchingIp'}

    assert restrict_region.generate_ip_address_policy(bucket_name, "eu-west-2") == {'Action': 's3:GetObject',
                                                                                    'Condition': {'NotIpAddress': {'aws:SourceIp': ['52.93.153.170/32',
                                                                                                                                    '2a05:d07a:c000::/40']},
                                                                                                  'Null': {'aws:sourceVpc': 'true'}},
                                                                                    'Effect': 'Deny',
                                                                                    'Principal': '*',
                                                                                    'Resource': 'arn:aws:s3:::'+bucket_name+'/*',
                                                                                    'Sid': 'DenyGetObjectForNonMatchingIp'}
