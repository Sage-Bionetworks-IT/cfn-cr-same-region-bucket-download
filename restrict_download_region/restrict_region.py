import os
import logging
import boto3
import json
import restrict_download_region.cfnresponse as cfnresponse
from contextlib import contextmanager
import requests

region = os.environ['REGION']
bucket_name = os.environ['BUCKET_NAME']
policy_statement_id = "DenyGetObjectForNonMatchingIp"
# have to put in a not None value for repsonseData or error will be thrown
empty_custom_resource_response_data = {'Data': ''}


def handler(event, context):
    """
    This lambda will either be triggered by a CloudFormation Custom Resource creation or by a recurring SNS topic
    """
    custom_resource_request_type = event.get('RequestType')

    # context manager for the case when this lambda is triggered by aws custom resource
    with handle_custom_resource_message(event, context):
        s3_client = boto3.client('s3')

        # get current bucket_policy from the s3 bucket
        try:
            bucket_policy = json.loads(
                s3_client.get_bucket_policy(Bucket=bucket_name)['Policy'])
        except Exception as e:
            bucket_policy = get_empty_policy()

        # filter out the previously set IP filtering policy
        bucket_policy['Statement'] = [statement for statement in bucket_policy['Statement'] if (
            policy_statement_id != statement.get("Sid"))]

        # when custom_resource_request_type is None, this lambda is being triggered by an SNS topic, not the CloudFormation Custom Resource
        if not custom_resource_request_type or custom_resource_request_type.lower() == 'create' or custom_resource_request_type.lower() == 'update':
            # add new IP address policy statement
            new_ip_policy_statement = generate_ip_address_policy()
            bucket_policy['Statement'].append(new_ip_policy_statement)

        # update existing policy or delete policy completely if there are no longer any policies left
        if bucket_policy != get_empty_policy():
            s3_client.put_bucket_policy(
                Bucket=bucket_name, Policy=json.dumps(bucket_policy))
        else:
            s3_client.delete_bucket_policy(Bucket=bucket_name)


def generate_ip_address_policy():
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
    return new_ip_policy_statement


def get_empty_policy():
    return {
        "Version": "2012-10-17",
        "Statement": []
    }


@contextmanager
def handle_custom_resource_message(event, context):
    custom_resource_request_type = event.get('RequestType')
    try:
        yield
        if custom_resource_request_type:
            cfnresponse.send(event, context, cfnresponse.SUCCESS,
                             empty_custom_resource_response_data)
        else:
            print("was not a custom resource. No messages sent")
    except Exception as e:
        print("\n\n")
        logging.exception(e)
        if custom_resource_request_type:
            cfnresponse.send(event, context, cfnresponse.FAILED,
                             empty_custom_resource_response_data)
        else:
            print("was not a custom resource. No messages sent")
        raise
