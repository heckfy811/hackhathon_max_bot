# src/models/request.py
from sqlalchemy import String, DateTime, Text, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
import uuid
from src.models import Base

class Request(Base):
    __tablename__ = "requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    guest_name: Mapped[str] = mapped_column(String(255), nullable=False)
    visit_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    visit_time: Mapped[str] = mapped_column(String(50))
    building: Mapped[str] = mapped_column(String(100))
    purpose: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        Enum("pending", "approved", "rejected", "need_clarification", "closed", name="request_status")
    )
    admin_comment: Mapped[str] = mapped_column(Text, nullable=True)
    clarification_question: Mapped[str] = mapped_column(Text, nullable=True)
    clarification_answer: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Внешние ключи
    initiator_id: Mapped[str] = mapped_column(String(255), ForeignKey("bot_schema.users.max_user_id"))

    # Связи (используем строки для отложенной загрузки)
    initiator: Mapped["User"] = relationship(back_populates="requests", foreign_keys=[initiator_id])
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="request")