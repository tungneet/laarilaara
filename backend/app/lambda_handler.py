"""AWS Lambda entrypoint.

API Gateway (HTTP API, payload format v2) invokes this handler through the
`ANY /{proxy+}` route. Mangum adapts the ASGI FastAPI app to the Lambda event
model. Configure the Lambda handler as ``app.lambda_handler.handler``.
"""
from __future__ import annotations

from mangum import Mangum

from app.main import app

handler = Mangum(app, lifespan="off")
