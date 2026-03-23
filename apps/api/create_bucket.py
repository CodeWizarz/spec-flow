import boto3
from botocore.client import Config

s3 = boto3.client(
    's3',
    endpoint_url='http://127.0.0.1:9000',
    aws_access_key_id='access-key',
    aws_secret_access_key='secret-key',
    config=Config(signature_version='s3v4'),
    region_name='us-east-1'
)

bucket_name = 'uploads'

try:
    s3.head_bucket(Bucket=bucket_name)
    print(f"Bucket '{bucket_name}' already exists.")
except Exception as e:
    # 404 Not Found means it doesn't exist
    if '404' in str(e):
        s3.create_bucket(Bucket=bucket_name)
        print(f"Created bucket: {bucket_name}")
        
        # Make the bucket public
        policy = '''{
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": [
                        "s3:GetObject"
                    ],
                    "Resource": [
                        "arn:aws:s3:::%s/*"
                    ]
                }
            ]
        }''' % bucket_name
        
        s3.put_bucket_policy(Bucket=bucket_name, Policy=policy)
        print("Set public read policy on bucket.")
    else:
        print(f"Error checking bucket: {e}")
