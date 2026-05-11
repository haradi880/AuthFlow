"""
AuthFlow Email Helper
---------------------
Stable Gmail SMTP SSL implementation
Optimized for Render deployment
"""

import smtplib
import socket
import ssl
import traceback

from email.message import EmailMessage

from flask import current_app


# =========================================================
# FORCE IPV4
# =========================================================

_original_getaddrinfo = socket.getaddrinfo


def force_ipv4():

    def ipv4_only(host, port, family=0, type=0, proto=0, flags=0):

        return _original_getaddrinfo(
            host,
            port,
            socket.AF_INET,
            type,
            proto,
            flags
        )

    socket.getaddrinfo = ipv4_only


# =========================================================
# SEND EMAIL
# =========================================================

def send_email(to_email, subject, body):

    server = None

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

        # =====================================================
        # LOGGING
        # =====================================================

        current_app.logger.info("=" * 60)
        current_app.logger.info("EMAIL DELIVERY STARTED")
        current_app.logger.info(f"TO: {to_email}")
        current_app.logger.info(f"SUBJECT: {subject}")

        current_app.logger.info("SMTP CONFIG")
        current_app.logger.info(f"SERVER: {mail_server}")
        current_app.logger.info(f"PORT: {mail_port}")
        current_app.logger.info(
            f"USERNAME EXISTS: {bool(mail_username)}"
        )
        current_app.logger.info(
            f"PASSWORD EXISTS: {bool(mail_password)}"
        )

        # =====================================================
        # VALIDATION
        # =====================================================

        if not mail_username or not mail_password:

            current_app.logger.error(
                "SMTP credentials missing."
            )

            return False

        # =====================================================
        # FORCE IPV4
        # =====================================================

        force_ipv4()

        current_app.logger.info(
            "IPv4 mode enabled."
        )

        # =====================================================
        # DNS TEST
        # =====================================================

        smtp_ip = socket.gethostbyname(mail_server)

        current_app.logger.info(
            f"{mail_server} resolved to {smtp_ip}"
        )

        # =====================================================
        # CREATE EMAIL
        # =====================================================

        msg = EmailMessage()

        msg["Subject"] = subject
        msg["From"] = f"AuthFlow <{mail_sender}>"
        msg["To"] = to_email

        msg.set_content(body)

        current_app.logger.info(
            "Email message created."
        )

        # =====================================================
        # SSL CONTEXT
        # =====================================================

        ssl_context = ssl.create_default_context()

        # =====================================================
        # CONNECT SMTP SSL
        # =====================================================

        current_app.logger.info(
            "Connecting to Gmail SMTP SSL..."
        )

        server = smtplib.SMTP_SSL(
            host=mail_server,
            port=mail_port,
            timeout=20,
            context=ssl_context
        )

        current_app.logger.info(
            "SMTP SSL connection established."
        )

        # =====================================================
        # DEBUG MODE
        # =====================================================

        server.set_debuglevel(1)

        # =====================================================
        # LOGIN
        # =====================================================

        current_app.logger.info(
            "Logging into Gmail..."
        )

        server.login(
            mail_username,
            mail_password
        )

        current_app.logger.info(
            "SMTP login successful."
        )

        # =====================================================
        # SEND EMAIL
        # =====================================================

        current_app.logger.info(
            "Sending email..."
        )

        server.send_message(msg)

        current_app.logger.info(
            "EMAIL SENT SUCCESSFULLY"
        )

        # =====================================================
        # CLOSE CONNECTION
        # =====================================================

        server.quit()

        current_app.logger.info(
            "SMTP connection closed."
        )

        current_app.logger.info("=" * 60)

        return True

    # =========================================================
    # AUTH ERROR
    # =========================================================

    except smtplib.SMTPAuthenticationError as e:

        current_app.logger.error(
            "SMTP AUTHENTICATION FAILED"
        )

        current_app.logger.error(str(e))

        traceback.print_exc()

        return False

    # =========================================================
    # CONNECTION ERROR
    # =========================================================

    except smtplib.SMTPConnectError as e:

        current_app.logger.error(
            "SMTP CONNECTION FAILED"
        )

        current_app.logger.error(str(e))

        traceback.print_exc()

        return False

    # =========================================================
    # SOCKET ERROR
    # =========================================================

    except socket.gaierror as e:

        current_app.logger.error(
            "DNS / NETWORK ERROR"
        )

        current_app.logger.error(str(e))

        traceback.print_exc()

        return False

    # =========================================================
    # TIMEOUT ERROR
    # =========================================================

    except socket.timeout as e:

        current_app.logger.error(
            "SMTP TIMEOUT ERROR"
        )

        current_app.logger.error(str(e))

        traceback.print_exc()

        return False

    # =========================================================
    # GENERAL ERROR
    # =========================================================

    except Exception as e:

        current_app.logger.error(
            "UNEXPECTED EMAIL ERROR"
        )

        current_app.logger.error(str(e))

        traceback.print_exc()

        return False

    # =========================================================
    # CLEANUP
    # =========================================================

    finally:

        try:

            if server:

                server.quit()

        except Exception:

            pass


# =========================================================
# OTP EMAIL
# =========================================================

def send_otp_email(email, otp):

    subject = "Your Verification Code - AuthFlow"

    body = f"""
Hello!

Your verification code is:

{otp}

This code will expire in 5 minutes.

If you did not request this verification code,
please ignore this email.

Best regards,
AuthFlow Team
"""

    return send_email(
        email,
        subject,
        body
    )


# =========================================================
# WELCOME EMAIL
# =========================================================

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