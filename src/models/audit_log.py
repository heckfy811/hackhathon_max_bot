import uuid

from sqlalchemy import String, Text, DateTime, ForeignKey, Integer, UUID, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from src.models import Base

class AuditLog(Base):
    __tablename__ = "audit_log"
    __table_args__ = {"schema": "bot_schema"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("bot_schema.requests.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(255), ForeignKey("bot_schema.users.max_user_id"), nullable=False)
    details: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("NOW()"), nullable=False)

    # Связи
    request: Mapped["Request"] = relationship(back_populates="audit_logs")
    actor: Mapped["User"] = relationship(back_populates="audit_actions")