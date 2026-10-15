from enum import Enum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Role(str, Enum):
    READER = "reader"
    EDITOR = "editor"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    __table_args__ = (
        CheckConstraint(
            "clearance >= 0 AND clearance <= 10",
            name="ck_users_clearance",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )

    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    role: Mapped[str] = mapped_column(
        String(20),
        default=Role.READER.value,
        nullable=False,
    )

    department: Mapped[str] = mapped_column(
        String(100),
        default="general",
        nullable=False,
    )

    clearance: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )


class Document(Base):
    __tablename__ = "documents"

    __table_args__ = (
        CheckConstraint(
            "classification >= 0 AND classification <= 10",
            name="ck_documents_classification",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    department: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    classification: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )