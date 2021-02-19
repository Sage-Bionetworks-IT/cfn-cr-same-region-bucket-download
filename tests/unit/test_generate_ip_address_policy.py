import restrict_download_region.restrict_region as restrict_region
from pytest_mock import MockerFixture


def test_generate_ip_address_policy(mocker: MockerFixture):
    bucket_name = "mytestbucket"
    # function under test

    ip_prefixes = ['15.230.56.104/31', '2600:1f19:8000::/36']

    assert restrict_region.generate_ip_address_policy(bucket_name, ip_prefixes) == {'Action': 's3:GetObject',
                                                                                    'Condition': {'NotIpAddress': {'aws:SourceIp': ['15.230.56.104/31', '2600:1f19:8000::/36']},
                                                                                                  'Null': {'aws:sourceVpc': 'true'}},
                                                                                    'Effect': 'Deny',
                                                                                    'Principal': '*',
                                                                                    'Resource': 'arn:aws:s3:::mytestbucket/*',
                                                                                    'Sid': 'DenyGetObjectForNonMatchingIp'}
