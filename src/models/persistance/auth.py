from sqlalchemy import (
    String,
    Integer,
    Text,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.core.db import Base


class Client(Base):
    __tablename__ = "clients"

    # OAuth identifiers
    client_id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        index=True,
    )

    client_id_issued_at: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # Metadata
    client_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="",
    )

    # ✅ SQLite-safe replacements
    redirect_uris: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
    )

    grant_types: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
    )

    response_types: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
    )

    token_endpoint_auth_method: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="none",
    )

    scope: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
