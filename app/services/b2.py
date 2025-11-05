import boto3, os

session = boto3.session.Session()
b2 = session.client(
    service_name="s3",
    endpoint_url=os.getenv("B2_ENDPOINT"),
    aws_access_key_id=os.getenv("B2_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("B2_SECRET_ACCESS_KEY"),
)

def upload_file(bucket: str, key: str, file_path: str) -> str:
    """Upload file to Backblaze B2 and return public URL"""
    b2.upload_file(file_path, bucket, key)
    return f"{os.getenv('B2_ENDPOINT')}/{bucket}/{key}"

def download_file(bucket: str, key: str, file_path: str):
    """Download file from Backblaze B2"""
    b2.download_file(bucket, key, file_path)

def delete_file(bucket: str, key: str):
    """Delete file from Backblaze B2"""
    b2.delete_object(Bucket=bucket, Key=key)
