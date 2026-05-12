"""
Production Email Helper
"""

import smtplib
import ssl

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from flask import current_app


def send_email(to_email, subject, body):

    try:

        # =====================================================
        # LOAD CONFIG
        # =====================================================

        mail_server = current_app.config.get(
            "MAIL_SERVER",
            "smtp.gmail.com"
        )

        mail_port = int(
            current_app.config.get(
                "MAIL_PORT",
                465
            )
        )

        mail_username = current_app.config.get(
            "MAIL_USERNAME"
        )

        mail_password = current_app.config.get(
            "MAIL_PASSWORD"
        )

        mail_sender = current_app.config.get(
            "MAIL_DEFAULT_SENDER",
            mail_username
        )

        mail_use_ssl = current_app.config.get(
            "MAIL_USE_SSL",
            True
        )

        # =====================================================
        # VALIDATION
        # =====================================================

        if not mail_username or not mail_password:

            current_app.logger.error(
                "Missing SMTP credentials."
            )

            return False

        # =====================================================
        # CREATE EMAIL
        # =====================================================

        msg = MIMEMultipart()

        msg["From"] = f"AuthFlow <{mail_sender}>"
        msg["To"] = to_email
        msg["Subject"] = subject

        msg.attach(
            MIMEText(body, "plain")
        )

        current_app.logger.info(
            f"Sending email to {to_email}"
        )

        # =====================================================
        # SSL CONNECTION
        # =====================================================

        if mail_use_ssl:

            context = ssl.create_default_context()

            with smtplib.SMTP_SSL(
                mail_server,
                mail_port,
                context=context,
                timeout=20
            ) as server:

                server.login(
                    mail_username,
                    mail_password
                )

                server.send_message(msg)

        # =====================================================
        # TLS CONNECTION
        # =====================================================

        else:

            with smtplib.SMTP(
                mail_server,
                587,
                timeout=20
            ) as server:

                server.starttls()

                server.login(
                    mail_username,
                    mail_password
                )

                server.send_message(msg)

        current_app.logger.info(
            "Email sent successfully."
        )

        return True

    except Exception as e:

        current_app.logger.error(
            f"Email sending failed: {str(e)}"
        )

        return False


def send_otp_email(email, otp):

    subject = "Your Verification Code - AuthFlow"

    body = f"""
Hello!

Your OTP code is:

{otp}

This code expires in 5 minutes.

If this was not you,
please ignore this email.

AuthFlow Team
"""

    return send_email(
        email,
        subject,
        body
    )


def send_welcome_email(email, username):

    subject = "Welcome to AuthFlow"

    body = f"""
Hello {username}!

Welcome to AuthFlow.

You can now:
- Publish blogs
- Upload projects
- Build your developer profile
- Connect with developers

Start building today.

AuthFlow Team
"""

    return send_email(
        email,
        subject,
        body
    )
