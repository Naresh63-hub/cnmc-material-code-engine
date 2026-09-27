from datetime import datetime

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    CheckConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class CNMCRegistry(Base):
    __tablename__ = "cnmc_registry"

    cnmc_code: Mapped[str] = mapped_column(
        String(30),
        primary_key=True,
    )

    canonical_description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    confidence_at_merge: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    merge_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    mappings = relationship(
        "CodeMapping",
        back_populates="cnmc",
        cascade="all, delete-orphan",
    )


class CodeMapping(Base):
    __tablename__ = "code_mapping"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    cnmc_code: Mapped[str] = mapped_column(
        ForeignKey("cnmc_registry.cnmc_code", ondelete="CASCADE"),
        nullable=False,
    )

    source_cpse: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    original_code: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    cnmc = relationship(
        "CNMCRegistry",
        back_populates="mappings",
    )

    __table_args__ = (
        UniqueConstraint(
            "source_cpse",
            "original_code",
            name="uq_cpse_original_code",
        ),
    )


class AuditLog(Base):
    __tablename__ = "audit_log"

    entry_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    cnmc_code: Mapped[str | None] = mapped_column(
        ForeignKey("cnmc_registry.cnmc_code", ondelete="SET NULL"),
        nullable=True,
    )

    action: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
    )

    actor: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    details: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=dict,
    )

    timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "action IN "
            "('auto_linked', 'human_approved', 'human_rejected', 'safety_gate_blocked')",
            name="ck_audit_action",
        ),
    )