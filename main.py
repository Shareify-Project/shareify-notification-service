"""
Shareify Notification Service
- Send email notifications via SMTP
"""

import os
import asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr
from email.message import EmailMessage
import aiosmtplib
import time
from fastapi import Request
from prometheus_client import make_asgi_app, Counter, Histogram

app = FastAPI(title="Shareify Notification Service", version="1.1.0")
# --
# -- POSTGRESQL HOTFIX: SQLite Polyfill Helper -------------------------------
import psycopg2
from psycopg2.extras import RealDictCursor

def db_execute(conn, query, vars=None):
    if '?' in query:
        query = query.replace('?', '%s')
    cursor = conn.cursor()
    cursor.execute(query, vars)
    return cursor
# ----------------------------------------------------------------------------

# ── Prometheus Metrics ──────────────────────────────────────────────────────
# Track HTTP request counts and latencies
REQUEST_COUNT = Counter(
    "http_requests_total", 
    "Total number of HTTP requests", 
    ["method", "endpoint", "http_status"]
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds", 
    "HTTP request latency in seconds", 
    ["method", "endpoint"]
)

# Mount the Prometheus ASGI app to expose the /metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

@app.middleware("http")
async def prometheus_middleware(request: Request, call_next):
    method = request.method
    endpoint = request.url.path
    
    # Do not track metrics for the metrics endpoint itself
    if endpoint == "/metrics":
        return await call_next(request)
        
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    # Update metrics
    REQUEST_COUNT.labels(method=method, endpoint=endpoint, http_status=response.status_code).inc()
    REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(process_time)
    
    return response


# ── SMTP Config ─────────────────────────────────────────────────────────────
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER)

class EmailRequest(BaseModel):
    to_email: str
    subject: str
    body: str

@app.post("/send-email")
async def send_email(request: EmailRequest):
    # If credentials are not set, fall back to mock logging
    if not SMTP_USER or not SMTP_PASSWORD:
        print(f"--- [MOCK EMAIL SENT (No Credentials)] ---")
        print(f"To: {request.to_email}")
        print(f"Subject: {request.subject}")
        print(f"Body: {request.body}")
        print(f"------------------------------------------")
        return {"message": "SMTP credentials not configured. Email logged to console."}

    message = EmailMessage()
    message["From"] = SMTP_FROM
    message["To"] = request.to_email
    message["Subject"] = request.subject
    message.set_content(request.body)

    try:
        await aiosmtplib.send(
            message,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            username=SMTP_USER,
            password=SMTP_PASSWORD,
            use_tls=(SMTP_PORT == 465),
            start_tls=(SMTP_PORT == 587),
        )
        return {"message": "Email sent successfully via SMTP"}
    except Exception as e:
        print(f"SMTP Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send email: {e}")

@app.get("/health")
def health():
    return {"status": "healthy", "service": "shareify-notification-service"}




