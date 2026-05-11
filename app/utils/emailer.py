"""
Production Email Helper for AuthFlow
------------------------------------
Features:
- Clean production structure
- IPv4 forced connection support
- TLS / SSL support
- Detailed logging
- Safe cleanup
- Better timeout handling
- Render deployment compatibility
"""

import smtplib
import socket
import ssl
import traceback

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from flask import current_app


# =========================================================
# FORCE IPV4
# =========================================================

_original_getaddrinfo = socket.getaddrinfo


def force_ipv4_only():
    """
    Force Python SMTP to use IPv4 only.
    Helps fix Render/Gmail networking issues.
    """

    def ipv4_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
        return _original_getaddrinfo(
            host,
            port,
            socket.AF_INET,
            type,
            proto,
            flags
        )

    socket.getaddrinfo = ipv4_getaddrinfo


# =========================================================
# MAIN EMAIL FUNCTION
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
                587
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

        mail_use_tls = str(
            current_app.config.get(
                "MAIL_USE_TLS",
                "true"
            )
        ).lower() == "true"

        mail_use_ssl = str(
            current_app.config.get(
                "MAIL_USE_SSL",
                "false"
            )
        ).lower() == "true"

        # =====================================================
        # DEBUG LOGGING
        # =====================================================

        current_app.logger.info("=" * 60)
        current_app.logger.info("EMAIL DELIVERY STARTED")
        current_app.logger.info(f"TO: {to_email}")
        current_app.logger.info(f"SUBJECT: {subject}")

        current_app.logger.info("SMTP CONFIG:")
        current_app.logger.info(f"MAIL_SERVER: {mail_server}")
        current_app.logger.info(f"MAIL_PORT: {mail_port}")
        current_app.logger.info(f"MAIL_USE_TLS: {mail_use_tls}")
        current_app.logger.info(f"MAIL_USE_SSL: {mail_use_ssl}")
        current_app.logger.info(
            f"MAIL_USERNAME EXISTS: {bool(mail_username)}"
        )
        current_app.logger.info(
            f"MAIL_PASSWORD EXISTS: {bool(mail_password)}"
        )

        # =====================================================
        # VALIDATION
        # =====================================================

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

        # =====================================================
        # FORCE IPV4
        # =====================================================

        current_app.logger.info(
            "Forcing IPv4 connection..."
        )

        force_ipv4_only()

        # =====================================================
        # DNS TEST
        # =====================================================

        try:

            smtp_ip = socket.gethostbyname(mail_server)

            current_app.logger.info(
                f"{mail_server} resolved to {smtp_ip}"
            )

        except Exception as dns_error:

            current_app.logger.error(
                "DNS resolution failed."
            )

            current_app.logger.error(str(dns_error))

            return False

        # =====================================================
        # CREATE EMAIL MESSAGE
        # =====================================================

        msg = MIMEMultipart()

        msg["From"] = f"AuthFlow <{mail_sender}>"
        msg["To"] = to_email
        msg["Subject"] = subject

        msg.attach(
            MIMEText(body, "plain")
        )

        current_app.logger.info(
            "Email message created."
        )

        # =====================================================
        # SMTP CONNECTION
        # =====================================================

        current_app.logger.info(
            "Connecting to SMTP server..."
        )

        socket.setdefaulttimeout(20)

        # =====================================================
        # SSL MODE
        # =====================================================

        if mail_use_ssl:

            current_app.logger.info(
                "Using SMTP SSL mode..."
            )

            ssl_context = ssl.create_default_context()

            server = smtplib.SMTP_SSL(
                host=mail_server,
                port=mail_port,
                timeout=20,
                context=ssl_context
            )

        # =====================================================
        # STANDARD MODE
        # =====================================================

        else:

            current_app.logger.info(
                "Using SMTP standard mode..."
            )

            server = smtplib.SMTP(
                host=mail_server,
                port=mail_port,
                timeout=20
            )

        current_app.logger.info(
            "SMTP socket connected."
        )

        # =====================================================
        # SMTP DEBUG
        # =====================================================

        server.set_debuglevel(1)

        # =====================================================
        # EHLO
        # =====================================================

        current_app.logger.info(
            "Sending EHLO..."
        )

        server.ehlo()

        current_app.logger.info(
            "EHLO successful."
        )

        # =====================================================
        # STARTTLS
        # =====================================================

        if mail_use_tls:

            current_app.logger.info(
                "Starting TLS encryption..."
            )

            tls_context = ssl.create_default_context()

            server.starttls(
                context=tls_context
            )

            server.ehlo()

            current_app.logger.info(
                "TLS started successfully."
            )

        # =====================================================
        # LOGIN
        # =====================================================

        current_app.logger.info(
            "Logging into SMTP..."
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
    # SMTP AUTH ERROR
    # =========================================================

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

    # =========================================================
    # SMTP CONNECT ERROR
    # =========================================================

    except smtplib.SMTPConnectError as e:

        current_app.logger.error(
            "SMTP CONNECTION FAILED"
        )

        current_app.logger.error(str(e))

        traceback.print_exc()

        return False

    # =========================================================
    # NETWORK ERROR
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