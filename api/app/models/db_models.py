"""
SQLAlchemy database models.
"""
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Boolean, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class GitConnectionDB(Base):
    """
    Database model for git provider connections.

    Stores OAuth tokens encrypted and manages token refresh.
    """

    __tablename__ = "git_connections"

    # Primary key
    id: Mapped[str] = mapped_column(String(32), primary_key=True)

    # Git provider info
    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    instance_url: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # User info
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Encrypted tokens (encrypted using Fernet)
    access_token_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Token metadata
    token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    scopes: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    # Connection metadata
    connected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    def __repr__(self) -> str:
        return f"<GitConnectionDB(id={self.id}, provider={self.provider}, username={self.username})>"
