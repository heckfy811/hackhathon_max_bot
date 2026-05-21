from sqlalchemy import String, Date, DateTime, Text, ForeignKey, text, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, date
from src.models import Base
import uuid

class Request(Base):
    __tablename__ = "requests"
    __table_args__ = {"schema": "bot_schema"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()")
    )
    short_id: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        server_default=text("generate_short_id()")
    )
    guest_name: Mapped[str] = mapped_column(String(255), nullable=True)
    visit_date: Mapped[date] = mapped_column(Date, nullable=True)
    visit_time: Mapped[str] = mapped_column(String(50), nullable=True)
    location: Mapped[str] = mapped_column(String(255), nullable=True)
    purpose: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), server_default=text("draft"), nullable=False)
    admin_comment: Mapped[str] = mapped_column(Text, nullable=True)
    rejection_reason: Mapped[str] = mapped_column(String(100), nullable=True)
    rejection_comment: Mapped[str] = mapped_column(Text, nullable=True)
    initiator_id: Mapped[str] = mapped_column(String(255), ForeignKey("bot_schema.users.max_user_id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("NOW()"), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("NOW()"), nullable=False)

    initiator: Mapped["User"] = relationship(back_populates="requests")
    clarifications: Mapped[list["Clarification"]] = relationship(back_populates="request")
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="request")