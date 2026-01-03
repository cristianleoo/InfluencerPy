import base64
import os
import logging
from typing import Optional

# Suppress OpenTelemetry warnings
logging.getLogger("opentelemetry.trace").setLevel(logging.ERROR)
logging.getLogger("opentelemetry.sdk.trace").setLevel(logging.ERROR)

def setup_langfuse() -> bool:
    """
    Setup Langfuse for tracing using OTLP.
    Returns True if setup was successful, False otherwise.
    """
    langfuse_host = os.getenv("LANGFUSE_HOST")
    langfuse_public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    langfuse_secret_key = os.getenv("LANGFUSE_SECRET_KEY")

    # Skip Langfuse setup if required environment variables are missing
    if not all([langfuse_host, langfuse_public_key, langfuse_secret_key]):
        return False

    # Build Basic Auth header
    langfuse_auth = base64.b64encode(
        f"{langfuse_public_key}:{langfuse_secret_key}".encode()
    ).decode()

    # Configure OpenTelemetry endpoint & headers (no /v1/traces suffix per docs)
    os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = (
        langfuse_host + "/api/public/otel"
    )
    os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = f"Authorization=Basic {langfuse_auth}"

    # Initialize Strands OTLP exporter
    try:
        from strands.telemetry import StrandsTelemetry
        # Check if already initialized or suppress the error if re-initialization isn't supported cleanly
        # The error "Overriding of current TracerProvider is not allowed" suggests global state is already set.
        # We can wrap this in a broader try/catch to ignore if it's already set.
        try:
            StrandsTelemetry().setup_otlp_exporter()
        except Exception as e:
            if "Overriding of current TracerProvider is not allowed" in str(e):
                # This is fine, it means it's already setup
                pass
            else:
                raise e
        return True
    except Exception as e:
        print(f"⚠️  Failed to initialize StrandsTelemetry OTLP exporter: {e}")
        return False
