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

app = FastAPI(title="Shareify Notification Service", version="1.1.0")

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


