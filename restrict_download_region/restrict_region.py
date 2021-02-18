import os
import logging
import botocore
import boto3
import json
import restrict_download_region.cfnresponse as cfnresponse
from contextlib import contextmanager
import requests

REGION = os.environ.get('REGION')
BUCKET_NAME = os.environ.get('BUCKET_NAME')
POLICY_STATEMENT_ID = "DenyGetObjectForNonMatchingIp"


def handler(event, context):
    """
    This lambda will either be triggered by a CloudFormation Custom Resource creation or by a recurring SNS topic
    """

    if not REGION or not BUCKET_NAME:
        raise ValueError("REGION and BUCKET_NAME must be defined.")

    # context manager for the case when this lambda is triggered by aws custom resource
    with handle_custom_resource_message(event, context):
        s3_client = boto3.client('s3')

        # get current bucket_policy from the s3 bucket
        bucket_policy = get_bucket_policy(s3_client, BUCKET_NAME)

        process_ip_restrict_policy(BUCKET_NAME, REGION, bucket_policy, event.get('RequestType'))

        update_bucket_policy(s3_client, BUCKET_NAME, bucket_policy)


def generate_ip_address_policy(bucket_name, region):
    # generate new policy statement based on data from AWS
    all_ip_ranges = requests.get('https://ip-ranges.amazonaws.com/ip-ranges.json').json()
    region_ip_addresses = ip_prefixes_for_region(all_ip_ranges['prefixes'], 'ip_prefix', region) + \
        ip_prefixes_for_region(all_ip_ranges['ipv6_prefixes'], 'ipv6_prefix', region)

    new_ip_policy_statement = {'Sid': POLICY_STATEMENT_ID,
                               'Effect': 'Deny',
                               'Principal': '*',
                               'Action': 's3:GetObject',
                               'Resource': 'arn:aws:s3:::'+bucket_name+'/*',
                               'Condition': {'NotIpAddress': {'aws:SourceIp': region_ip_addresses}}}
    # allows any S3 VPC Endpoint to bypass the ip restriction.
    # cross region gateway endpoints are not supported in AWS so any S3 VPC endpoint
    # traffic is implicitly same region.
    new_ip_policy_statement['Condition']['Null'] = {'aws:sourceVpc': 'true'}
    return new_ip_policy_statement


def get_bucket_policy(s3_client, bucket_name):
    try:
        return json.loads(s3_client.get_bucket_policy(Bucket=bucket_name)['Policy'])
    except botocore.exceptions.ClientError as e:
        print(e)
        if e.response['Error']['Code'] == 'NoSuchBucketPolicy':
            return {
                "Version": "2012-10-17",
                "Statement": []
            }
        else:
            raise


def process_ip_restrict_policy(bucket_name, region, custom_resource_request_type, bucket_policy):
    """
    Modifies the passed in bucket_policy and decides whether to add or remove the IP restriciting policy
    """
    a = {"foo": "bar"}
    # filter out the previously set IP filtering policy
    bucket_policy['Statement'] = [statement for statement in bucket_policy['Statement']
                                  if (POLICY_STATEMENT_ID != statement.get("Sid"))]

    # when custom_resource_request_type is None, this lambda is being triggered by an SNS topic, not the CloudFormation Custom Resource
    if not custom_resource_request_type or custom_resource_request_type.lower() == 'create' or custom_resource_request_type.lower() == 'update':
        # add new IP address policy statement
        new_ip_policy_statement = generate_ip_address_policy(bucket_name, region)
        bucket_policy['Statement'].append(new_ip_policy_statement)


def update_bucket_policy(s3_client, bucket_name, bucket_policy):
    # update existing policy or delete policy completely if there are no longer any policies left
    if bucket_policy['Statement']:
        s3_client.put_bucket_policy(Bucket=bucket_name, Policy=json.dumps(bucket_policy))
    else:
        s3_client.delete_bucket_policy(Bucket=bucket_name)


def ip_prefixes_for_region(ip_ranges, prefix_key, region):
    return [item[prefix_key] for item in ip_ranges if (
        item["service"] == "AMAZON" and item["region"] == region)]


@contextmanager
def handle_custom_resource_message(event, context):
    custom_resource_request_type = event.get('RequestType')
    try:
        yield
        if custom_resource_request_type:
            cfnresponse.send(event, context, cfnresponse.SUCCESS, {'Data': ''})
        else:
            print("was not a custom resource. No messages sent")
    except Exception as e:
        print("\n\n")
        logging.exception(e)
        if custom_resource_request_type:
            cfnresponse.send(event, context, cfnresponse.FAILED, {'Data': ''})
        else:
            print("was not a custom resource. No messages sent")
        raise
