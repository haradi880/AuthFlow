"""
Advanced Email Helper for AuthFlow
----------------------------------
Features:
- Detailed SMTP debugging
- TLS/SSL support
- Safe connection handling
- Better logging
- Timeout protection
- Render deployment debugging
"""

import smtplib
import socket
import ssl
import traceback

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from flask import current_app


def send_email(to_email, subject, body):
    """
    Send email with advanced debugging and error handling.
    """

    server = None

    try:
        # =========================================================
        # LOAD CONFIG
        # =========================================================

        mail_server = current_app.config.get("MAIL_SERVER")
        mail_port = int(current_app.config.get("MAIL_PORT", 587))

        mail_username = current_app.config.get("MAIL_USERNAME")
        mail_password = current_app.config.get("MAIL_PASSWORD")

        mail_sender = current_app.config.get(
            "MAIL_DEFAULT_SENDER",
            mail_username
        )

        mail_use_tls = str(
            current_app.config.get("MAIL_USE_TLS", "true")
        ).lower() == "true"

        mail_use_ssl = str(
            current_app.config.get("MAIL_USE_SSL", "false")
        ).lower() == "true"

        # =========================================================
        # CONFIG DEBUGGING
        # =========================================================

        current_app.logger.info("=" * 60)
        current_app.logger.info("STARTING EMAIL DELIVERY")
        current_app.logger.info("TO: %s", to_email)
        current_app.logger.info("SUBJECT: %s", subject)

        current_app.logger.info("SMTP CONFIG:")
        current_app.logger.info("MAIL_SERVER: %s", mail_server)
        current_app.logger.info("MAIL_PORT: %s", mail_port)
        current_app.logger.info("MAIL_USE_TLS: %s", mail_use_tls)
        current_app.logger.info("MAIL_USE_SSL: %s", mail_use_ssl)
        current_app.logger.info("MAIL_USERNAME EXISTS: %s", bool(mail_username))
        current_app.logger.info("MAIL_PASSWORD EXISTS: %s", bool(mail_password))

        # =========================================================
        # VALIDATION
        # =========================================================

        if not mail_username or not mail_password:
            current_app.logger.error(
                "SMTP credentials missing."
            )
            return False

        if mail_use_tls and mail_use_ssl:
            current_app.logger.error(
                "TLS and SSL cannot both be enabled."
            )
            return False

        # =========================================================
        # CREATE MESSAGE
        # =========================================================

        msg = MIMEMultipart()

        msg["From"] = f"AuthFlow <{mail_sender}>"
        msg["To"] = to_email
        msg["Subject"] = subject

        msg.attach(MIMEText(body, "plain"))

        current_app.logger.info("Email message created successfully.")

        # =========================================================
        # SMTP CONNECTION
        # =========================================================

        current_app.logger.info(
            "Connecting to SMTP server..."
        )

        # SSL MODE
        if mail_use_ssl:

            current_app.logger.info(
                "Using SSL connection..."
            )

            context = ssl.create_default_context()

            server = smtplib.SMTP_SSL(
                mail_server,
                mail_port,
                timeout=20,
                context=context
            )

        # TLS / NORMAL MODE
        else:

            current_app.logger.info(
                "Using standard SMTP connection..."
            )

            server = smtplib.SMTP(
                mail_server,
                mail_port,
                timeout=20
            )

        current_app.logger.info(
            "SMTP connection established."
        )

        # SHOW SMTP DEBUG OUTPUT
        server.set_debuglevel(1)

        # =========================================================
        # EHLO
        # =========================================================

        server.ehlo()

        current_app.logger.info(
            "EHLO completed successfully."
        )

        # =========================================================
        # START TLS
        # =========================================================

        if mail_use_tls:

            current_app.logger.info(
                "Starting TLS encryption..."
            )

            server.starttls()

            server.ehlo()

            current_app.logger.info(
                "TLS started successfully."
            )

        # =========================================================
        # LOGIN
        # =========================================================

        current_app.logger.info(
            "Logging into SMTP server..."
        )

        server.login(
            mail_username,
            mail_password
        )

        current_app.logger.info(
            "SMTP login successful."
        )

        # =========================================================
        # SEND EMAIL
        # =========================================================

        current_app.logger.info(
            "Sending email..."
        )

        server.send_message(msg)

        current_app.logger.info(
            "EMAIL SENT SUCCESSFULLY."
        )

        # =========================================================
        # CLOSE CONNECTION
        # =========================================================

        server.quit()

        current_app.logger.info(
            "SMTP connection closed."
        )

        current_app.logger.info("=" * 60)

        return True

    # =============================================================
    # SMTP AUTH ERROR
    # =============================================================

    except smtplib.SMTPAuthenticationError as e:

        current_app.logger.error(
            "SMTP AUTHENTICATION FAILED"
        )

        current_app.logger.error(str(e))

        current_app.logger.error(
            "Check Gmail App Password."
        )

        traceback.print_exc()

        return False

    # =============================================================
    # SMTP CONNECTION ERROR
    # =============================================================

    except smtplib.SMTPConnectError as e:

        current_app.logger.error(
            "SMTP CONNECTION FAILED"
        )

        current_app.logger.error(str(e))

        traceback.print_exc()

        return False

    # =============================================================
    # NETWORK ERROR
    # =============================================================

    except socket.gaierror as e:

        current_app.logger.error(
            "DNS / NETWORK ERROR"
        )

        current_app.logger.error(str(e))

        traceback.print_exc()

        return False

    # =============================================================
    # TIMEOUT ERROR
    # =============================================================

    except socket.timeout as e:

        current_app.logger.error(
            "SMTP CONNECTION TIMEOUT"
        )

        current_app.logger.error(str(e))

        traceback.print_exc()

        return False

    # =============================================================
    # GENERAL ERROR
    # =============================================================

    except Exception as e:

        current_app.logger.error(
            "UNEXPECTED EMAIL ERROR"
        )

        current_app.logger.error(str(e))

        traceback.print_exc()

        return False

    # =============================================================
    # CLEANUP
    # =============================================================

    finally:

        try:
            if server:
                server.quit()
        except:
            pass


# ================================================================
# OTP EMAIL
# ================================================================

def send_otp_email(email, otp):

    subject = "Your Verification Code - AuthFlow"

    body = f"""
Hello!

Your verification code is:

{otp}

This code will expire in 5 minutes.

If you did not request this code,
please ignore this email.

Best regards,
AuthFlow Team
"""

    return send_email(
        email,
        subject,
        body
    )


# ================================================================
# WELCOME EMAIL
# ================================================================

def send_welcome_email(email, username):

    subject = "Welcome to AuthFlow!"

    body = f"""
Hello {username}!

Welcome to AuthFlow.

You can now:
- Publish blogs
- Share projects
- Build your developer profile
- Connect with developers

Start building today.

Best regards,
AuthFlow Team
"""

    return send_email(
        email,
        subject,
        body
    )