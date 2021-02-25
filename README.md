# cfn-cr-same-region-bucket-download
Add restriction on S3 bucket to only allow download from AWS resources
in the same region.
This function will be automatically re-triggered by Amazon's SNS topic because the IP address ranges will periodically change.

### Important Implementation Detail
This Lambda is being used as a AWS Custom Resource, but it is **not a singleton Lambda** that gets reused to process each Custom Resource request. Each provision **S3 bucket will need to create it's own dedicated instance** of this Lambda because the SNS event of Amazon's constantly updating IP ranges is does not include any information about the bucket to change, so we can not rely on only Custom Resource event handling. An alternative implementation would be to have a single Lambda on each SNS update from Amazon handle policy updates for every region-restricted bucket, but this apporach would introduces more complexity if any off the policy updates fail.




## Development

### Contributions
Contributions are welcome.

### Requirements
Run `pipenv install --dev` to install both production and development
requirements, and `pipenv shell` to activate the virtual environment. For more
information see the [pipenv docs](https://pipenv.pypa.io/en/latest/).

After activating the virtual environment, run `pre-commit install` to install
the [pre-commit](https://pre-commit.com/) git hook.

### Create a local build

```shell script
sam build
```

### Run unit tests
Tests are defined in the `tests` folder in this project. Use PIP to install the
[pytest](https://docs.pytest.org/en/latest/) and run unit tests.

```shell script
python -m pytest tests/ -vv
```

### Run integration tests
Running integration tests
[requires docker](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/sam-cli-command-reference-sam-local-start-api.html)

**Remember to update the `"BucketName"` of `env_vars.json` with the name of the bucket you wish to test!**

Swap out the event file in the `events/` directory. `update.json` and `create.json` should result in the same behavior. `delete.json` will remove the IP restricting policy from the bucket specified in the
You may also need to include as an argument the AWS Profile  (e.g. `--profile scipooldev-admin`)
```shell script
sam local invoke RestrictBucketDownloadRegionFunction --event events/create.json --env-vars env_vars.json
```

## Deployment

### Deploy Lambda to S3
Deployments are sent to the
[Sage cloudformation repository](https://bootstrap-awss3cloudformationbucket-19qromfd235z9.s3.amazonaws.com/index.html)
which requires permissions to upload to Sage
`bootstrap-awss3cloudformationbucket-19qromfd235z9` and
`essentials-awss3lambdaartifactsbucket-x29ftznj6pqw` buckets.

```shell script
sam package --profile=admincentral-cfndeployer --template-file .aws-sam/build/template.yaml \
  --s3-bucket essentials-awss3lambdaartifactsbucket-x29ftznj6pqw \
  --output-template-file .aws-sam/build/cfn-cr-same-region-bucket-download-template.yaml

aws s3 cp --profile=admincentral-cfndeployer .aws-sam/build/cfn-cr-same-region-bucket-download-template.yaml s3://bootstrap-awss3cloudformationbucket-19qromfd235z9/cfn-cr-same-region-bucket-download/master/
```

## Publish Lambda

### Private access
Publishing the lambda makes it available in your AWS account.  It will be accessible in
the [serverless application repository](https://console.aws.amazon.com/serverlessrepo).

```shell script
sam publish --template .aws-sam/build/cfn-cr-same-region-bucket-download-template.yaml
```

### Public access
Making the lambda publicly accessible makes it available in the
[global AWS serverless application repository](https://serverlessrepo.aws.amazon.com/applications)

```shell script
aws serverlessrepo put-application-policy \
  --application-id <lambda ARN> \
  --statements Principals=*,Actions=Deploy
```

## Install Lambda into AWS

### Sceptre
Create the following [sceptre](https://github.com/Sceptre/sceptre) file
config/prod/cfn-cr-same-region-bucket-download-template.yaml

```yaml
template_path: "remote/cfn-cr-same-region-bucket-download-template.yaml"
stack_name: "cfn-cr-same-region-bucket-download"
stack_tags:
  Department: "Platform"
  Project: "Infrastructure"
  OwnerEmail: "it@sagebase.org"
hooks:
  before_launch:
    - !cmd "curl https://bootstrap-awss3cloudformationbucket-19qromfd235z9.s3.amazonaws.com/cfn-cr-same-region-bucket-download/master/cfn-cr-same-region-bucket-download-template.yaml --create-dirs -o templates/remote/cfn-cr-same-region-bucket-download-template.yaml"
```

Install the lambda using sceptre:
```shell script
sceptre --var "profile=my-profile" --var "region=us-east-1" launch prod/cfn-cr-same-region-bucket-download-template.yaml
```

### AWS Console
Steps to deploy from AWS console.

1. Login to AWS
2. Access the
[serverless application repository](https://console.aws.amazon.com/serverlessrepo)
-> Available Applications
3. Select application to install
4. Enter Application settings
5. Click Deploy

## Releasing

We have setup our CI to automate a releases.  To kick off the process just create
a tag (i.e 0.0.1) and push to the repo.  The tag must be the same number as the current
version in [template.yaml](template.yaml).  Our CI will do the work of deploying and publishing
the lambda.
