import os
import getpass
import smtplib
import ssl
from pathlib import Path

env_file = Path(__file__).parent / ".env"

if env_file.exists():
    from dotenv import dotenv_values
    for key, value in dotenv_values(env_file).items():
        if value is not None:
            os.environ.setdefault(key, value)

email_user = os.getenv("EMAIL_HOST_USER", "").strip()
email_password = os.getenv("EMAIL_HOST_PASSWORD", "").strip()

if not email_user:
    email_user = input("Enter your Gmail address: ").strip()

if not email_password:
    email_password = getpass.getpass(
        "Enter your Google App Password (input hidden): "
    ).strip()

try:
    print("\nConnecting to Gmail on port 587...")

    with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as server:
        server.set_debuglevel(1)
        server.ehlo()
        server.starttls(context=ssl.create_default_context())
        server.ehlo()

        print("\nTesting SMTP authentication...")
        server.login(email_user, email_password)

        print("\nSUCCESS: Gmail SMTP authentication worked!")

except Exception as exc:
    print(f"\nFAILED: {type(exc).__name__}: {exc}")
