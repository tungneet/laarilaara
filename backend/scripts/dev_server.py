"""Run the real API over HTTP with a local moto AWS server.

Local development server: `uvicorn` serves `app.main:app` on 127.0.0.1:8000
while DynamoDB/S3 calls go to a threaded moto HTTP server. This makes local S3
upload URLs reachable by a browser. No AWS account, credentials, or Docker are
required, and all state resets on restart.

Usage (from backend/):
    .\\.venv\\Scripts\\python.exe scripts\\dev_server.py [--port 8000]
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Location-independent: resolve backend/ from this file and make it both the
# working directory (so config.yaml/.env are found) and the import root.
_BACKEND_DIR = Path(__file__).resolve().parent.parent
os.chdir(_BACKEND_DIR)
sys.path.insert(0, str(_BACKEND_DIR))

# Fake credentials so boto3 never signs anything real, even if the developer
# has live credentials in their environment or ~/.aws.
os.environ["AWS_ACCESS_KEY_ID"] = "testing"
os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
os.environ["AWS_SESSION_TOKEN"] = "testing"
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--moto-port", type=int, default=5000)
    args = parser.parse_args()

    moto_endpoint = f"http://127.0.0.1:{args.moto_port}"
    os.environ["LAARA_STORAGE__DYNAMODB_ENDPOINT_URL"] = moto_endpoint
    os.environ["LAARA_STORAGE__S3_ENDPOINT_URL"] = moto_endpoint

    from moto.server import ThreadedMotoServer

    moto_server = ThreadedMotoServer(
        ip_address="127.0.0.1", port=args.moto_port, verbose=False
    )
    moto_server.start()

    try:
        from app.core import dynamodb, s3
        from app.core.config import get_settings

        settings = get_settings()

        dynamodb.get_table.cache_clear()
        dynamodb.create_table_if_missing()

        s3.get_s3_client.cache_clear()
        client = s3.get_s3_client()
        for bucket in (
            settings.storage.media_bucket_name,
            settings.storage.artifacts_bucket_name,
            settings.storage.embeddings_bucket_name,
        ):
            client.create_bucket(Bucket=bucket)

        client.put_bucket_cors(
            Bucket=settings.storage.media_bucket_name,
            CORSConfiguration={
                "CORSRules": [
                    {
                        "AllowedOrigins": settings.cors_allowed_origins,
                        "AllowedMethods": ["GET", "PUT", "HEAD"],
                        "AllowedHeaders": ["*"],
                        "ExposeHeaders": ["ETag"],
                        "MaxAgeSeconds": 3000,
                    }
                ]
            },
        )

        import uvicorn

        from app.main import app

        # Keep one process in control of both server lifecycles. Reload is
        # deliberately unsupported because it would start a second process.
        uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    finally:
        moto_server.stop()


if __name__ == "__main__":
    main()
