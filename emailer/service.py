import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

def sendEmail(emailAddress: str, title: str, message: str):
    email_host = os.getenv("EMAIL_HOST")
    email_port = int(os.getenv("EMAIL_PORT"))
    email_user = os.getenv("EMAIL_HOST_USER")
    email_password = os.getenv("EMAIL_HOST_PASSWORD")

    msg = MIMEMultipart()
    msg["From"] = email_user
    msg["To"] = emailAddress
    msg["Subject"] = title

    msg.attach(MIMEText(message, "plain"))

    try:
        server = smtplib.SMTP(email_host, email_port)
        server.starttls()
        server.login(email_user, email_password)
        server.send_message(msg)
        server.quit()
        print("Email sent successfully!")
    except Exception as e:
        print("Email sending error:", e)