from datetime import datetime, timedelta

from flask import url_for
from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


blog_tags = db.Table(
    "blog_tags",
    db.Column("blog_id", db.Integer, db.ForeignKey("blogs.id", ondelete="CASCADE"), primary_key=True),
    db.Column("tag_id", db.Integer, db.ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)

project_tags = db.Table(
    "project_tags",
    db.Column("project_id", db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True),
    db.Column("tag_id", db.Integer, db.ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)

devlog_tags = db.Table(
    "devlog_tags",
    db.Column("devlog_id", db.Integer, db.ForeignKey("devlogs.id", ondelete="CASCADE"), primary_key=True),
    db.Column("tag_id", db.Integer, db.ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class TimestampMixin:
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class User(UserMixin, TimestampMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(120))
    headline = db.Column(db.String(160))
    bio = db.Column(db.String(500))
    location = db.Column(db.String(120))
    website = db.Column(db.String(255))
    resume_url = db.Column(db.String(500))
    avatar = db.Column(db.String(255), default="default.jpg")
    banner = db.Column(db.String(255), default="default_banner.jpg")
    skills = db.Column(db.String(500))
    twitter = db.Column(db.String(255))
    linkedin = db.Column(db.String(255))
    github = db.Column(db.String(255))
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    active = db.Column("is_active", db.Boolean, default=True, nullable=False)
    failed_login_count = db.Column(db.Integer, default=0, nullable=False)
    locked_until = db.Column(db.DateTime)
    featured_blog_id = db.Column(db.Integer, db.ForeignKey("blogs.id", ondelete="SET NULL"), index=True)
    featured_project_id = db.Column(db.Integer, db.ForeignKey("projects.id", ondelete="SET NULL"), index=True)
    pending_email = db.Column(db.String(255))
    email_on_messages = db.Column(db.Boolean, default=True, nullable=False)
    email_on_comments = db.Column(db.Boolean, default=True, nullable=False)
    email_on_follows = db.Column(db.Boolean, default=True, nullable=False)
    email_on_likes = db.Column(db.Boolean, default=False, nullable=False)
    weekly_digest = db.Column(db.Boolean, default=True, nullable=False)
    message_permission = db.Column(db.String(20), default="everyone", nullable=False)
    profile_views_count = db.Column(db.Integer, default=0, nullable=False)
    xp_total = db.Column(db.Integer, default=0, nullable=False, index=True)
    level = db.Column(db.Integer, default=1, nullable=False, index=True)
    profile_xp_awarded_at = db.Column(db.DateTime)

    blogs = db.relationship("Blog", back_populates="author", lazy="dynamic", cascade="all, delete-orphan", foreign_keys="Blog.user_id")
    projects = db.relationship("Project", back_populates="author", lazy="dynamic", cascade="all, delete-orphan", foreign_keys="Project.user_id")
    devlogs = db.relationship("DevLog", back_populates="author", lazy="dynamic", cascade="all, delete-orphan")
    comments = db.relationship("Comment", back_populates="author", lazy="dynamic", cascade="all, delete-orphan")
    otp_tokens = db.relationship("OTPToken", back_populates="user", lazy="dynamic", cascade="all, delete-orphan")
    received_notifications = db.relationship(
        "Notification",
        foreign_keys="Notification.user_id",
        back_populates="user",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    xp_transactions = db.relationship("XPTransaction", back_populates="user", lazy="dynamic", cascade="all, delete-orphan")

    followed = db.relationship(
        "Follow",
        foreign_keys="Follow.follower_id",
        back_populates="follower",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    followers = db.relationship(
        "Follow",
        foreign_keys="Follow.followed_id",
        back_populates="followed",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    @property
    def is_active(self):
        return self.active

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_locked(self):
        return bool(self.locked_until and self.locked_until > datetime.utcnow())

    def register_failed_login(self, max_attempts=5, lock_minutes=15):
        self.failed_login_count = (self.failed_login_count or 0) + 1
        if self.failed_login_count >= max_attempts:
            self.locked_until = datetime.utcnow() + timedelta(minutes=lock_minutes)

    def clear_failed_logins(self):
        self.failed_login_count = 0
        self.locked_until = None

    def increment_failed_login(self, max_attempts=5, lock_minutes=15):
        self.register_failed_login(max_attempts, lock_minutes)
        db.session.commit()

    def reset_failed_logins(self):
        self.clear_failed_logins()
        db.session.commit()

    def get_skills_list(self):
        return [skill.strip() for skill in (self.skills or "").split(",") if skill.strip()]

    def profile_completion(self):
        checks = [
            bool(self.full_name),
            bool(self.headline),
            bool(self.bio and len(self.bio) >= 40),
            bool(self.location),
            bool(self.website),
            bool(self.resume_url),
            bool(self.github),
            bool(self.linkedin),
            len(self.get_skills_list()) >= 3,
            bool(self.avatar and self.avatar != "default.jpg"),
            bool(self.banner and self.banner != "default_banner.jpg"),
        ]
        completed = sum(1 for item in checks if item)
        return round((completed / len(checks)) * 100)

    @property
    def xp_progress(self):
        try:
            from app.services.gamification import xp_progress

            return xp_progress(self.xp_total or 0)
        except Exception:
            return {"level": self.level or 1, "current": 0, "needed": 100, "percent": 0}

    def set_skills_list(self, skills_list):
        self.skills = ",".join(skill.strip() for skill in skills_list if skill.strip())

    def follow(self, user):
        if user.id != self.id and not self.is_following(user):
            db.session.add(Follow(follower_id=self.id, followed_id=user.id))

    def unfollow(self, user):
        follow = self.followed.filter_by(followed_id=user.id).first()
        if follow:
            db.session.delete(follow)

    def is_following(self, user):
        return user and self.followed.filter_by(followed_id=user.id).first() is not None

    def followers_count(self):
        return self.followers.count()

    def following_count(self):
        return self.followed.count()

    @property
    def avatar_url(self):
        return url_for("uploaded_file", folder="avatars", filename=self.avatar) if self.avatar else ""

    @property
    def banner_url(self):
        return url_for("uploaded_file", folder="banners", filename=self.banner) if self.banner else ""

    @property
    def social(self):
        return {"twitter": self.twitter, "linkedin": self.linkedin, "github": self.github}

    def __str__(self):
        return self.username

    def __getitem__(self, index):
        return self.username[index]


class Follow(db.Model):
    __tablename__ = "follows"

    id = db.Column(db.Integer, primary_key=True)
    follower_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    followed_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    follower = db.relationship("User", foreign_keys=[follower_id], back_populates="followed")
    followed = db.relationship("User", foreign_keys=[followed_id], back_populates="followers")

    __table_args__ = (db.UniqueConstraint("follower_id", "followed_id", name="uq_follow_pair"),)


class XPTransaction(db.Model):
    __tablename__ = "xp_transactions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    action = db.Column(db.String(50), nullable=False, index=True)
    points = db.Column(db.Integer, nullable=False)
    source_type = db.Column(db.String(50), index=True)
    source_id = db.Column(db.Integer, index=True)
    meta = db.Column(db.JSON)
    awarded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    bucket_key = db.Column(db.String(120), index=True)

    user = db.relationship("User", back_populates="xp_transactions")

    __table_args__ = (
        db.UniqueConstraint("user_id", "action", "source_type", "source_id", name="uq_xp_source_once"),
        db.UniqueConstraint("user_id", "action", "bucket_key", name="uq_xp_bucket_once"),
    )


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.String(255))

    blogs = db.relationship("Blog", back_populates="category", lazy="dynamic")
    projects = db.relationship("Project", back_populates="category", lazy="dynamic")

    def __str__(self):
        return self.name


class Tag(db.Model):
    __tablename__ = "tags"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False, index=True)

    def __str__(self):
        return self.name


class Blog(TimestampMixin, db.Model):
    __tablename__ = "blogs"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(220), unique=True, nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    excerpt = db.Column(db.String(500))
    thumbnail = db.Column(db.String(255))
    status = db.Column(db.String(20), default="draft", nullable=False, index=True)
    reading_time = db.Column(db.Integer, default=1, nullable=False)
    views_count = db.Column(db.Integer, default=0, nullable=False)
    likes_count = db.Column(db.Integer, default=0, nullable=False)
    comments_count = db.Column(db.Integer, default=0, nullable=False)
    published_at = db.Column(db.DateTime, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id", ondelete="SET NULL"), index=True)

    author = db.relationship("User", back_populates="blogs", foreign_keys=[user_id])
    category = db.relationship("Category", back_populates="blogs")
    tags = db.relationship("Tag", secondary=blog_tags, lazy="subquery", backref=db.backref("blogs", lazy=True))
    comments = db.relationship("Comment", back_populates="blog", lazy="dynamic", cascade="all, delete-orphan")
    likes = db.relationship("BlogLike", back_populates="blog", lazy="dynamic", cascade="all, delete-orphan")
    bookmarks = db.relationship("Bookmark", back_populates="blog", lazy="dynamic", cascade="all, delete-orphan")

    @property
    def thumbnail_url(self):
        return url_for("uploaded_file", folder="blogs", filename=self.thumbnail) if self.thumbnail else ""

    @property
    def author_bio(self):
        return self.author.bio if self.author else ""

    @property
    def author_full_bio(self):
        return self.author.bio if self.author else ""

    @property
    def author_skills(self):
        return self.author.get_skills_list() if self.author else []

    @property
    def followers_count(self):
        return self.author.followers_count() if self.author else 0

    @property
    def total_blogs(self):
        return self.author.blogs.filter_by(status="published").count() if self.author else 0

    def calculate_reading_time(self):
        self.reading_time = max(1, round(len((self.content or "").split()) / 200))

    def is_liked_by(self, user):
        return bool(user and getattr(user, "is_authenticated", False) and BlogLike.query.filter_by(blog_id=self.id, user_id=user.id).first())

    def is_bookmarked_by(self, user):
        return bool(user and getattr(user, "is_authenticated", False) and Bookmark.query.filter_by(blog_id=self.id, user_id=user.id).first())

    def get_absolute_url(self):
        return url_for("blog.blog_detail", slug=self.slug)


class Project(TimestampMixin, db.Model):
    __tablename__ = "projects"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(220), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    thumbnail = db.Column(db.String(255))
    github_url = db.Column(db.String(500))
    demo_url = db.Column(db.String(500))
    stars_count = db.Column(db.Integer, default=0, nullable=False)
    status = db.Column(db.String(20), default="draft", nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id", ondelete="SET NULL"), index=True)

    author = db.relationship("User", back_populates="projects", foreign_keys=[user_id])
    category = db.relationship("Category", back_populates="projects")
    tags = db.relationship("Tag", secondary=project_tags, lazy="subquery", backref=db.backref("projects", lazy=True))
    images = db.relationship("ProjectImage", back_populates="project", lazy="dynamic", cascade="all, delete-orphan")
    stars = db.relationship("ProjectStar", back_populates="project", lazy="dynamic", cascade="all, delete-orphan")

    @property
    def thumbnail_url(self):
        return url_for("uploaded_file", folder="projects", filename=self.thumbnail) if self.thumbnail else ""

    @property
    def tech_stack(self):
        return [tag.name for tag in self.tags]

    def get_absolute_url(self):
        return url_for("project.project_detail", slug=self.slug)

    def is_starred_by(self, user):
        return bool(user and getattr(user, "is_authenticated", False) and ProjectStar.query.filter_by(project_id=self.id, user_id=user.id).first())


class ProjectStar(db.Model):
    __tablename__ = "project_stars"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    project = db.relationship("Project", back_populates="stars")
    user = db.relationship("User", backref=db.backref("project_stars", lazy="dynamic", cascade="all, delete-orphan"))

    __table_args__ = (db.UniqueConstraint("user_id", "project_id", name="uq_project_star"),)


class ProjectImage(db.Model):
    __tablename__ = "project_images"

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    caption = db.Column(db.String(200))
    order = db.Column(db.Integer, default=0, nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)

    project = db.relationship("Project", back_populates="images")

    @property
    def url(self):
        return url_for("uploaded_file", folder="projects", filename=self.filename)


class DevLog(TimestampMixin, db.Model):
    __tablename__ = "devlogs"

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    progress = db.Column(db.Integer, default=0, nullable=False, index=True)
    milestone = db.Column(db.String(160))
    is_pinned = db.Column(db.Boolean, default=False, nullable=False, index=True)
    visibility = db.Column(db.String(20), default="public", nullable=False, index=True)
    likes_count = db.Column(db.Integer, default=0, nullable=False)
    comments_count = db.Column(db.Integer, default=0, nullable=False)
    reposts_count = db.Column(db.Integer, default=0, nullable=False)
    bookmarks_count = db.Column(db.Integer, default=0, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    author = db.relationship("User", back_populates="devlogs")
    tags = db.relationship("Tag", secondary=devlog_tags, lazy="subquery", backref=db.backref("devlogs", lazy=True))
    media = db.relationship("DevLogMedia", back_populates="devlog", order_by="DevLogMedia.order", cascade="all, delete-orphan")
    comments = db.relationship("DevLogComment", back_populates="devlog", lazy="dynamic", cascade="all, delete-orphan")
    likes = db.relationship("DevLogLike", back_populates="devlog", lazy="dynamic", cascade="all, delete-orphan")
    bookmarks = db.relationship("DevLogBookmark", back_populates="devlog", lazy="dynamic", cascade="all, delete-orphan")
    reposts = db.relationship("DevLogRepost", back_populates="devlog", lazy="dynamic", cascade="all, delete-orphan")

    @property
    def preview(self):
        return (self.content or "").strip()[:180]

    @property
    def trending_score(self):
        return (
            (self.likes_count or 0) * 3
            + (self.comments_count or 0) * 4
            + (self.reposts_count or 0) * 5
            + (self.bookmarks_count or 0)
            + min(self.progress or 0, 100)
        )

    def is_liked_by(self, user):
        return bool(user and getattr(user, "is_authenticated", False) and DevLogLike.query.filter_by(devlog_id=self.id, user_id=user.id).first())

    def is_bookmarked_by(self, user):
        return bool(user and getattr(user, "is_authenticated", False) and DevLogBookmark.query.filter_by(devlog_id=self.id, user_id=user.id).first())

    def is_reposted_by(self, user):
        return bool(user and getattr(user, "is_authenticated", False) and DevLogRepost.query.filter_by(devlog_id=self.id, user_id=user.id).first())

    def get_absolute_url(self):
        return url_for("devlogs.detail", devlog_id=self.id)


class DevLogMedia(db.Model):
    __tablename__ = "devlog_media"

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    media_type = db.Column(db.String(20), default="image", nullable=False)
    alt_text = db.Column(db.String(200))
    order = db.Column(db.Integer, default=0, nullable=False)
    devlog_id = db.Column(db.Integer, db.ForeignKey("devlogs.id", ondelete="CASCADE"), nullable=False, index=True)

    devlog = db.relationship("DevLog", back_populates="media")

    @property
    def url(self):
        return url_for("uploaded_file", folder="devlogs", filename=self.filename)


class DevLogComment(TimestampMixin, db.Model):
    __tablename__ = "devlog_comments"

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    devlog_id = db.Column(db.Integer, db.ForeignKey("devlogs.id", ondelete="CASCADE"), nullable=False, index=True)

    author = db.relationship("User", backref=db.backref("devlog_comments", lazy="dynamic", cascade="all, delete-orphan"))
    devlog = db.relationship("DevLog", back_populates="comments")


class DevLogLike(db.Model):
    __tablename__ = "devlog_likes"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    devlog_id = db.Column(db.Integer, db.ForeignKey("devlogs.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    devlog = db.relationship("DevLog", back_populates="likes")
    user = db.relationship("User", backref=db.backref("devlog_likes", lazy="dynamic", cascade="all, delete-orphan"))

    __table_args__ = (db.UniqueConstraint("user_id", "devlog_id", name="uq_devlog_like"),)


class DevLogBookmark(db.Model):
    __tablename__ = "devlog_bookmarks"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    devlog_id = db.Column(db.Integer, db.ForeignKey("devlogs.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    devlog = db.relationship("DevLog", back_populates="bookmarks")
    user = db.relationship("User", backref=db.backref("devlog_bookmarks", lazy="dynamic", cascade="all, delete-orphan"))

    __table_args__ = (db.UniqueConstraint("user_id", "devlog_id", name="uq_devlog_bookmark"),)


class DevLogRepost(db.Model):
    __tablename__ = "devlog_reposts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    devlog_id = db.Column(db.Integer, db.ForeignKey("devlogs.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    devlog = db.relationship("DevLog", back_populates="reposts")
    user = db.relationship("User", backref=db.backref("devlog_reposts", lazy="dynamic", cascade="all, delete-orphan"))

    __table_args__ = (db.UniqueConstraint("user_id", "devlog_id", name="uq_devlog_repost"),)


class Comment(TimestampMixin, db.Model):
    __tablename__ = "comments"

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey("comments.id", ondelete="CASCADE"), index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    blog_id = db.Column(db.Integer, db.ForeignKey("blogs.id", ondelete="CASCADE"), nullable=False, index=True)

    author = db.relationship("User", back_populates="comments")
    blog = db.relationship("Blog", back_populates="comments")
    replies = db.relationship("Comment", backref=db.backref("parent", remote_side=[id]), lazy="dynamic", cascade="all, delete-orphan")

    @property
    def likes(self):
        return 0


class BlogLike(db.Model):
    __tablename__ = "blog_likes"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    blog_id = db.Column(db.Integer, db.ForeignKey("blogs.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    blog = db.relationship("Blog", back_populates="likes")
    user = db.relationship("User", backref=db.backref("blog_likes", lazy="dynamic", cascade="all, delete-orphan"))

    __table_args__ = (db.UniqueConstraint("user_id", "blog_id", name="uq_blog_like"),)


class Bookmark(db.Model):
    __tablename__ = "bookmarks"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    blog_id = db.Column(db.Integer, db.ForeignKey("blogs.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    blog = db.relationship("Blog", back_populates="bookmarks")
    user = db.relationship("User", backref=db.backref("bookmarks", lazy="dynamic", cascade="all, delete-orphan"))

    __table_args__ = (db.UniqueConstraint("user_id", "blog_id", name="uq_bookmark"),)


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    action = db.Column(db.String(50), nullable=False, index=True)
    message = db.Column(db.String(500), nullable=False)
    link = db.Column(db.String(500))
    is_read = db.Column(db.Boolean, default=False, nullable=False, index=True)
    from_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    user = db.relationship("User", foreign_keys=[user_id], back_populates="received_notifications")
    from_user = db.relationship("User", foreign_keys=[from_user_id])


class OTPToken(db.Model):
    __tablename__ = "otp_tokens"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    purpose = db.Column(db.String(30), nullable=False, index=True)
    code_hash = db.Column(db.String(255), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    consumed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", back_populates="otp_tokens")

    def set_code(self, code):
        self.code_hash = generate_password_hash(code)

    def verify(self, code):
        return not self.consumed_at and self.expires_at > datetime.utcnow() and check_password_hash(self.code_hash, code)


class Message(db.Model):
    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    recipient_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    sender = db.relationship("User", foreign_keys=[sender_id], backref=db.backref("sent_messages", lazy="dynamic"))
    recipient = db.relationship("User", foreign_keys=[recipient_id], backref=db.backref("received_messages", lazy="dynamic"))


class Block(db.Model):
    __tablename__ = "blocks"

    id = db.Column(db.Integer, primary_key=True)
    blocker_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    blocked_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    blocker = db.relationship("User", foreign_keys=[blocker_id], backref=db.backref("blocks_made", lazy="dynamic", cascade="all, delete-orphan"))
    blocked = db.relationship("User", foreign_keys=[blocked_id], backref=db.backref("blocks_received", lazy="dynamic", cascade="all, delete-orphan"))

    __table_args__ = (db.UniqueConstraint("blocker_id", "blocked_id", name="uq_block_pair"),)


class Report(db.Model):
    __tablename__ = "reports"

    id = db.Column(db.Integer, primary_key=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), index=True)
    reported_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    reason = db.Column(db.String(80), nullable=False)
    details = db.Column(db.String(1000))
    status = db.Column(db.String(20), default="open", nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    reporter = db.relationship("User", foreign_keys=[reporter_id])
    reported_user = db.relationship("User", foreign_keys=[reported_user_id], backref=db.backref("reports_received", lazy="dynamic"))
