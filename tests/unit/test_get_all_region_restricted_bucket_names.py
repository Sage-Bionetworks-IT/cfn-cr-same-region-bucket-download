import boto3
from botocore.stub import Stubber
import restrict_download_region.restrict_region as restrict_region


def test_get_all_region_restricted_bucket_names(mocker):
    response = {'PaginationToken': 'paginatiotoken1',
                'ResourceTagMappingList': [{'ResourceARN': 'arn:aws:s3:::first-bucket',
                                            'Tags': [{'Key': 'single-region-access', 'Value': ''}]}],
                'ResponseMetadata': {'RequestId': '11111111-1111-1111-1111-111111111111',
                                     'HTTPStatusCode': 200,
                                     'HTTPHeaders': {'x-amzn-requestid': '11111111-1111-1111-1111-111111111111',
                                                     'content-type': 'application/x-amz-json-1.1',
                                                     'content-length': '751',
                                                     'date': 'Fri, 19 Feb 2021 00:45:19 GMT'},
                                     'RetryAttempts': 0}}

    response2 = {'PaginationToken': 'paginationtoken2',
                 'ResourceTagMappingList': [{'ResourceARN': 'arn:aws:s3:::second-bucket', 'Tags': [{'Key': 'single-region-access', 'Value': ''}]}],
                 'ResponseMetadata': {'RequestId': '22222222-2222-2222-2222-222222222222',
                                      'HTTPStatusCode': 200,
                                      'HTTPHeaders': {'x-amzn-requestid': '22222222-2222-2222-2222-222222222222',
                                                      'content-type': 'application/x-amz-json-1.1',
                                                      'content-length': '748',
                                                      'date': 'Fri, 19 Feb 2021 00:45:19 GMT'},
                                      'RetryAttempts': 0}}

    response3 = {'PaginationToken': '',
                 'ResourceTagMappingList': [],
                 'ResponseMetadata': {'RequestId': '33333333-3333-3333-3333-333333333333',
                                      'HTTPStatusCode': 200, 'HTTPHeaders': {'x-amzn-requestid': '33333333-3333-3333-3333-333333333333',
                                                                             'content-type': 'application/x-amz-json-1.1',
                                                                             'content-length': '50',
                                                                             'date': 'Fri, 19 Feb 2021 00:45:19 GMT'},
                                      'RetryAttempts': 0}}

    tagging = boto3.client('resourcegroupstaggingapi')
    mocker.patch.object(boto3, 'client', return_value=tagging, autospec=True)
    stubber = Stubber(tagging)
    stubber.add_response('get_resources', response)
    stubber.add_response('get_resources', response2)
    stubber.add_response('get_resources', response3)

    with stubber:
        assert restrict_region.get_all_region_restricted_bucket_names() == ['first-bucket', 'second-bucket']
