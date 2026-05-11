import logging
import os
import secrets
from pathlib import Path
from logging.handlers import RotatingFileHandler

from flask import Flask, abort, redirect, render_template, request, send_from_directory, session, url_for
from flask_login import current_user
from jinja2 import TemplateNotFound
from sqlalchemy import inspect

from config import config_by_name
from app.extensions import db, login_manager, migrate


def create_app(config_name=None):
    app = Flask(__name__)
    config_name = config_name or os.getenv("FLASK_ENV") or os.getenv("APP_ENV") or "default"
    app.config.from_object(config_by_name.get(config_name, config_by_name["default"]))

    init_extensions(app)
    register_blueprints(app)
    register_security(app)
    register_template_helpers(app)
    register_error_handlers(app)
    register_upload_route(app)
    register_cli(app)
    ensure_upload_folders(app)
    ensure_runtime_schema(app)
    configure_logging(app)

    return app


def init_extensions(app):
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "info"

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    @login_manager.unauthorized_handler
    def unauthorized():
        if request.blueprint == "api":
            return {"error": "Authentication required"}, 401
        return redirect(url_for("auth.login", next=request.url))


def register_blueprints(app):
    from app.routes.admin import admin_bp
    from app.routes.api import api_bp
    from app.routes.auth import auth_bp
    from app.routes.blog import blog_bp
    from app.routes.devlogs import devlog_bp
    from app.routes.main import main_bp
    from app.routes.project import project_bp
    from app.routes.social import social_bp
    from app.routes.messages import messages_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(blog_bp)
    app.register_blueprint(devlog_bp)
    app.register_blueprint(project_bp)
    app.register_blueprint(social_bp)
    app.register_blueprint(messages_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(api_bp, url_prefix="/api")


def register_security(app):
    @app.before_request
    def sync_login_session():
        if current_user.is_authenticated:
            if session.get("user") != current_user.username:
                session["user"] = current_user.username
            if session.get("is_admin") != current_user.is_admin:
                session["is_admin"] = current_user.is_admin
        return None

    @app.before_request
    def csrf_protect():
        if not app.config.get("WTF_CSRF_ENABLED", True):
            return None
        if request.method in {"GET", "HEAD", "OPTIONS", "TRACE"}:
            return None
        if request.path.startswith("/api/"):
            return None
        token = session.get("_csrf_token")
        submitted = request.form.get("_csrf_token") or request.headers.get("X-CSRFToken")
        if not token or not submitted or not secrets.compare_digest(token, submitted):
            abort(400, description="Invalid CSRF token")
        return None

    @app.after_request
    def add_security_headers(response):
        for header, value in app.config.get("SECURITY_HEADERS", {}).items():
            response.headers.setdefault(header, value)
        if request.endpoint == "static":
            response.cache_control.public = True
            response.cache_control.max_age = 604800
            response.headers["Cache-Control"] = "public, max-age=604800"
        elif request.endpoint == "uploaded_file":
            response.cache_control.public = True
            response.cache_control.max_age = 86400
        elif request.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store, max-age=0"
            response.headers["Pragma"] = "no-cache"
        elif request.method == "GET":
            if current_user.is_authenticated or request.endpoint in {
                "auth.login",
                "auth.register",
                "auth.verify_signup",
                "auth.forgot_password",
                "auth.reset_verify",
                "auth.new_password",
            }:
                response.headers["Cache-Control"] = "no-store, max-age=0"
                response.headers["Pragma"] = "no-cache"
                response.headers["Expires"] = "0"
            else:
                response.headers["Cache-Control"] = "public, max-age=120"
        return response


def register_template_helpers(app):
    @app.context_processor
    def inject_globals():
        from app.models import Notification, Message, Bookmark
        from flask_login import current_user
        
        counts = {'notifications': 0, 'messages': 0, 'bookmarks': 0}
        if current_user.is_authenticated:
            counts['notifications'] = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
            counts['messages'] = Message.query.filter_by(recipient_id=current_user.id, is_read=False).count()
            counts['bookmarks'] = Bookmark.query.filter_by(user_id=current_user.id).count()
            
        if "_csrf_token" not in session:
            session["_csrf_token"] = secrets.token_urlsafe(32)
            
        return {
            "csrf_token": lambda: session["_csrf_token"],
            "unread_counts": counts
        }

    @app.template_filter("upload_url")
    def upload_url(filename, folder):
        return url_for("uploaded_file", folder=folder, filename=filename) if filename else ""


def register_upload_route(app):
    @app.get("/uploads/<folder>/<path:filename>", endpoint="uploaded_file")
    def uploaded_file(folder, filename):
        allowed_folders = {"avatars", "banners", "blogs", "projects", "devlogs"}
        if folder not in allowed_folders:
            abort(404)
        return send_from_directory(Path(app.config["UPLOAD_FOLDER"]) / folder, filename)


def register_cli(app):
    @app.cli.command("init-db")
    def init_db_command():
        from app.models import Category, User

        db.create_all()
        if not Category.query.first():
            for name, slug in (
                ("AI & Machine Learning", "ai-ml"),
                ("Web Development", "web-dev"),
                ("Mobile Development", "mobile-dev"),
                ("DevOps & Cloud", "devops"),
                ("Data Science", "data-science"),
            ):
                db.session.add(Category(name=name, slug=slug))
        if not User.query.filter_by(email="admin@example.com").first():
            admin = User(username="admin", email="admin@example.com", is_admin=True, is_verified=True)
            admin.set_password(os.getenv("ADMIN_PASSWORD", "change-me-admin"))
            db.session.add(admin)
        db.session.commit()
        print("Database initialized.")


def register_error_handlers(app):
    @app.errorhandler(429)
    def too_many_requests(error):
        return render_template("errors/400.html", error=error) if _template_exists(app, "errors/400.html") else (str(error), 429)

    @app.errorhandler(400)
    def bad_request(error):
        return render_template("errors/400.html", error=error) if _template_exists(app, "errors/400.html") else (str(error), 400)

    @app.errorhandler(403)
    def forbidden(error):
        if _template_exists(app, "errors/403.html"):
            return render_template("errors/403.html"), 403
        return "Access denied", 403

    @app.errorhandler(404)
    def not_found(error):
        if _template_exists(app, "errors/404.html"):
            return render_template("errors/404.html"), 404
        return "Page not found", 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        app.logger.exception("Unhandled server error")
        if _template_exists(app, "errors/500.html"):
            return render_template("errors/500.html"), 500
        return "Internal server error", 500


def _template_exists(app, template_name):
    try:
        app.jinja_env.loader.get_source(app.jinja_env, template_name)
        return True
    except TemplateNotFound:
        return False


def ensure_upload_folders(app):
    for folder in ("avatars", "banners", "blogs", "projects", "devlogs"):
        Path(app.config["UPLOAD_FOLDER"], folder).mkdir(parents=True, exist_ok=True)


def ensure_runtime_schema(app):
    """Additive SQLite-only compatibility for local dev databases."""
    if not app.config.get("SQLALCHEMY_DATABASE_URI", "").startswith("sqlite"):
        return

    additions = {
        "headline": "VARCHAR(160)",
        "resume_url": "VARCHAR(500)",
        "featured_blog_id": "INTEGER",
        "featured_project_id": "INTEGER",
        "pending_email": "VARCHAR(255)",
        "email_on_messages": "BOOLEAN NOT NULL DEFAULT 1",
        "email_on_comments": "BOOLEAN NOT NULL DEFAULT 1",
        "email_on_follows": "BOOLEAN NOT NULL DEFAULT 1",
        "email_on_likes": "BOOLEAN NOT NULL DEFAULT 0",
        "weekly_digest": "BOOLEAN NOT NULL DEFAULT 1",
        "message_permission": "VARCHAR(20) NOT NULL DEFAULT 'everyone'",
        "profile_views_count": "INTEGER NOT NULL DEFAULT 0",
        "xp_total": "INTEGER NOT NULL DEFAULT 0",
        "level": "INTEGER NOT NULL DEFAULT 1",
        "profile_xp_awarded_at": "DATETIME",
    }

    with app.app_context():
        inspector = inspect(db.engine)
        if not inspector.has_table("users"):
            return
        existing = {column["name"] for column in inspector.get_columns("users")}
        with db.engine.begin() as connection:
            for name, column_type in additions.items():
                if name not in existing:
                    connection.exec_driver_sql(f"ALTER TABLE users ADD COLUMN {name} {column_type}")


def configure_logging(app):
    logging.basicConfig(level=logging.INFO if not app.debug else logging.DEBUG)
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    handler = RotatingFileHandler(log_dir / "app.log", maxBytes=1_000_000, backupCount=3)
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s"))
    if not any(isinstance(h, RotatingFileHandler) for h in app.logger.handlers):
        app.logger.addHandler(handler)
