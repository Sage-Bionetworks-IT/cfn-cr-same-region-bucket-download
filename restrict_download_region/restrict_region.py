import json
import boto3
import os
import cfnresponse
from botocore.vendored import requests
DEFAULT_EMPTY_POLICY = {
    "Version": "2012-10-17",
    "Statement": []
}

MISSING_BUCKET_NAME_ERROR_MESSAGE = 'BucketName parameter is required'

region = os.environ['REGION']
policy_statement_id = "DenyGetObjectForNonMatchingIp"
# have to put in a not None value for repsonseData or error will be thrown
custom_resource_response_data = {'Data': ''}


def handler(event, context):
    """
    This lambda will either be triggered by a CloudFormation Custom Resource creation or by a recurring SNS topic
    """
    try:
        bucket_name = get_bucket_name(event)
        # for the case when this lambda is triggered by aws custom resource
        custom_resource_request_type = event.get('RequestType')
        s3_client = boto3.client('s3')
        # get current bucket_policy from the s3 bucket and remove old policy if it exists
        try:
            bucket_policy = json.loads(
                s3_client.get_bucket_policy(Bucket=bucket_name)['Policy'])
        except:
            bucket_policy = DEFAULT_EMPTY_POLICY.copy()
        bucket_policy['Statement'] = [statement for statement in bucket_policy['Statement'] if (
            policy_statement_id != statement.get("Sid"))]
        # when custom_resource_request_type is None, this lambda is being triggered by the SNS topic, not the CloudFormation custom resource
        if not custom_resource_request_type or custom_resource_request_type == 'Create' or custom_resource_request_type == 'Update':
            # generate new policy statement based on data from AWS
            ip_ranges = requests.get(
                'https://ip-ranges.amazonaws.com/ip-ranges.json').json()['prefixes']
            region_ip_addresses = [item['ip_prefix'] for item in ip_ranges if (
                item["service"] == "AMAZON" and item["region"] == region)]
            new_ip_policy_statement = {'Sid': policy_statement_id,
                                       'Effect': 'Deny',
                                       'Principal': '*',
                                       'Action': 's3:GetObject',
                                       'Resource': 'arn:aws:s3:::'+bucket_name+'/*',
                                       'Condition': {'NotIpAddress': {'aws:SourceIp': region_ip_addresses}}}
            # allows any S3 VPC Endpoint to bypass the ip restriction.
            # cross region gateway endpoints are not supported in AWS so any S3 VPC endpoint
            # traffic is implicitly same region.
            new_ip_policy_statement['Condition']['Null'] = {
                'aws:sourceVpc': 'true'}
            # add new IP address policy statement
            bucket_policy['Statement'].append(new_ip_policy_statement)
        s3_client.put_bucket_policy(
            Bucket=bucket_name, Policy=json.dumps(bucket_policy))
        if custom_resource_request_type:
            cfnresponse.send(event, context, cfnresponse.SUCCESS,
                             custom_resource_response_data)
    except Exception as e:
        print(e)
        cfnresponse.send(event, context, cfnresponse.FAILED,
                         custom_resource_response_data)
        raise


def get_bucket_name(event):
    '''Get the bucket name from event params sent to lambda'''
    resource_properties = event.get('ResourceProperties')
    bucket_name = resource_properties.get('BucketName')
    if not bucket_name:
        print(json.dumps(event))
        raise ValueError(MISSING_BUCKET_NAME_ERROR_MESSAGE)
    return bucket_name
