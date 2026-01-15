from celery import shared_task
import time
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# SMTP Configuration (Use environment variables for security)
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp-relay.sendinblue.com")
SMTP_PORT = os.getenv("SMTP_PORT", 587)
SMTP_USER = os.getenv("SMTP_USER")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")

@shared_task
def send_email_task(email: str, token: str):
    msg = MIMEMultipart("alternative")
    BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:5173")
    activation_link = f"{BASE_URL}/activate?user_email={email}&activation_token={token}"
    msg["Subject"] = "Activate Your Account"
    msg["From"] = "<noreply@theallset.in>"
    msg["To"] = email
    text_content = f"Hello! Please activate your account by clicking Below."
    html_content = f"""
    <html>
      <body>
        <p>Hello!</p>
        <p>Please click the button below to activate your account:</p>
        <a href="{activation_link}" 
           style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
           Activate Account
        </a>
        <br>
        <p>Thank you!</p>
      </body>
    </html>
    """
    msg.attach(MIMEText(text_content, "plain"))
    msg.attach(MIMEText(html_content, "html"))
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SENDER_PASSWORD)
            server.sendmail(msg["From"], [email], msg.as_string())
        return {"status": "sent", "to": email}
    except Exception as e:
        return {"status": "error", "message": str(e)}
