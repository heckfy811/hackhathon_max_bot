from sqlalchemy import String, Boolean, DateTime, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from src.models import Base

class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "bot_schema"}

    max_user_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    consent_given: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_version: Mapped[str] = mapped_column(String(50), nullable=True)
    consent_timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    role: Mapped[str] = mapped_column(String(50), default="user")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("NOW()"), nullable=False)

    # Связи
    requests: Mapped[list["Request"]] = relationship(back_populates="initiator")
    clarifications_asked: Mapped[list["Clarification"]] = relationship(
        foreign_keys="Clarification.asked_by",
        back_populates="asker"
    )
    audit_actions: Mapped[list["AuditLog"]] = relationship(
        foreign_keys="AuditLog.actor_id",
        back_populates="actor"
    )