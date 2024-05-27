import boto3
import os

aws_access_key_id = "AKIA32L5MJWELTOGVDOA"
aws_secret_access_key = "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"
aws_region = "ap-northeast-2"
bucket_name = 'toongether-s3'
s3_base_folder = 'ciphermask'

s3_client = boto3.client(
    's3',
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key,
    region_name=aws_region
)


def upload_file_to_s3(file_path, object_name=None):
    """S3에 파일을 업로드하고 S3 URL을 반환"""
    try:
        if object_name is None:
            object_name = os.path.basename(file_path)

        s3_object_key = f"{s3_base_folder}/{object_name}"

        # 파일 업로드
        s3_client.upload_file(file_path, bucket_name, s3_object_key)
        print(f"File {file_path} uploaded to {bucket_name}/{s3_object_key}")

        # S3 URL 생성
        s3_url = f"cdn.toongether.kr/{s3_object_key}"
        return s3_url

    except FileNotFoundError:
        print("The file was not found")
        return None
