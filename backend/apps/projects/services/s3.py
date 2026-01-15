import aioboto3
import mimetypes

class S3Service:
    def __init__(self, bucket: str, region: str = "us-east-1"):
        self.bucket = bucket
        self.region = region
        self.session = aioboto3.Session()

    async def add(self, file_obj, key: str):
        content_type, _ = mimetypes.guess_type(key)
        if content_type is None:
            content_type = "application/octet-stream"

        async with self.session.client("s3", region_name=self.region) as client:
            await client.upload_fileobj(
                Fileobj=file_obj,
                Bucket=self.bucket,
                Key=key,
                ExtraArgs={"ContentType": content_type}
            )

    async def remove(self, key: str):
        async with self.session.client("s3", region_name=self.region) as client:
            await client.delete_object(Bucket=self.bucket, Key=key)

    async def delete_prefix(self, prefix: str):
        async with self.session.client("s3", region_name=self.region) as client:
            paginator = client.get_paginator("list_objects_v2")
            async for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
                objects = page.get("Contents", [])
                if not objects:
                    continue
                await client.delete_objects(
                    Bucket=self.bucket,
                    Delete={"Objects": [{"Key": obj["Key"]} for obj in objects], "Quiet": True},
                )


# Singleton instance
s3 = S3Service(bucket="aws-manas-generic-sites")
