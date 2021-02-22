import os
import logging
import botocore
import boto3
import json
import restrict_download_region.cfnresponse as cfnresponse
from contextlib import contextmanager
import requests
from typing import List, Dict, Optional, Tuple
import itertools
import traceback

# AWS_REGION should always be defined in the context of a lambda
AWS_REGION = os.environ.get('AWS_REGION')
BUCKET_NAME = os.environ.get('BUCKET_NAME')

POLICY_STATEMENT_ID = "DenyGetObjectForNonMatchingIp"
SINGLE_REGION_BUCKET_TAG = 'single-region-access'


def handler(event: dict, context: dict):
    """
    This lambda will either be triggered by a CloudFormation Custom Resource
    creation or by a recurring SNS topic
    """
    # context manager for the case when this lambda is triggered by aws custom resource
    with handle_custom_resource_status_message(event, context) as custom_resource_request_type:
        if not BUCKET_NAME:
            raise ValueError("BUCKET_NAME must be defined in enviroment variables")

        region_ip_prefixes = get_ip_prefixes_for_region() \
            if custom_resource_request_type != 'Delete'\
            else None

        s3_client = boto3.client('s3')

        # get current bucket_policy from the s3 bucket
        bucket_policy = get_bucket_policy(s3_client, BUCKET_NAME)

        # add/update/remove ip restirction policy depending on whether region_ip_prefixes
        process_ip_restrict_policy(BUCKET_NAME, region_ip_prefixes,
                                   custom_resource_request_type, bucket_policy)

        # update with newly modified bucket policy
        update_bucket_policy(s3_client, BUCKET_NAME, bucket_policy)


def generate_ip_address_policy(bucket_name: str, region_ip_prefixes: List[str]):
    return {
        'Sid': POLICY_STATEMENT_ID,
        'Effect': 'Deny',
        'Principal': '*',
        'Action': 's3:GetObject',
        'Resource': 'arn:aws:s3:::'+bucket_name+'/*',
        'Condition': {
            'NotIpAddress': {'aws:SourceIp': region_ip_prefixes},
            # allows any S3 VPC Endpoint to bypass the ip restriction.
            # cross region gateway endpoints are not supported in AWS so any S3 VPC endpoint
            # traffic is implicitly same region.
            'Null': {'aws:sourceVpc': 'true'}
        }
    }


def get_ip_prefixes_for_region() -> List[str]:
    if not AWS_REGION:
        raise ValueError("AWS_REGION must be defined in environment variables.")

    # generate new policy statement based on data from AWS
    all_ip_prefixes = requests.get('https://ip-ranges.amazonaws.com/ip-ranges.json').json()
    return ip_prefixes_for_region(all_ip_prefixes['prefixes'], 'ip_prefix', AWS_REGION) + \
        ip_prefixes_for_region(all_ip_prefixes['ipv6_prefixes'], 'ipv6_prefix', AWS_REGION)


def get_bucket_policy(s3_client, bucket_name: str) -> dict:
    try:
        return json.loads(s3_client.get_bucket_policy(Bucket=bucket_name)['Policy'])
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchBucketPolicy':
            return {
                "Version": "2012-10-17",
                "Statement": []
            }
        else:
            raise


def process_ip_restrict_policy(bucket_name: str,
                               region_ip_prefixes: List[str],
                               custom_resource_request_type: str,
                               bucket_policy: dict):
    """
    Modifies the passed in bucket_policy and decides whether
    to add or remove the IP restriction policy
    """
    # filter out the previously set IP filtering policy
    bucket_policy['Statement'] = [statement for statement in bucket_policy['Statement']
                                  if (POLICY_STATEMENT_ID != statement.get("Sid"))]

    # skip adding new policy if deleting the custom resource
    if custom_resource_request_type == 'Delete':
        return

    # add new IP address policy statement
    new_ip_policy_statement = generate_ip_address_policy(bucket_name, region_ip_prefixes)
    bucket_policy['Statement'].append(new_ip_policy_statement)


def update_bucket_policy(s3_client, bucket_name: str, bucket_policy: dict):
    # update existing policy or delete policy completely if there are no longer any policies left
    if bucket_policy['Statement']:
        s3_client.put_bucket_policy(Bucket=bucket_name, Policy=json.dumps(bucket_policy))
    else:
        s3_client.delete_bucket_policy(Bucket=bucket_name)


def ip_prefixes_for_region(ip_ranges: List[Dict], prefix_key: str, region: str) -> List[str]:
    return [item[prefix_key] for item in ip_ranges if (
        item["service"] == "AMAZON" and item["region"] == region)]


@contextmanager
def handle_custom_resource_status_message(event: dict, context: dict):
    custom_resource_request_type = event.get('RequestType')
    try:
        yield custom_resource_request_type

        # when custom_resource_request_type is None, this lambda is being
        # triggered by Amazon's SNS topic because IP prefixes have updated
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
