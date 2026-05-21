import uuid

from sqlalchemy import String, Text, DateTime, ForeignKey, Boolean, UUID, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from src.models import Base

class Clarification(Base):
    __tablename__ = "clarifications"
    __table_args__ = {"schema": "bot_schema"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()")
    )
    request_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("bot_schema.requests.id"), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=True)
    asked_by: Mapped[str] = mapped_column(String(255), ForeignKey("bot_schema.users.max_user_id"), nullable=False)
    asked_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("NOW()"), nullable=False)
    answered_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Связи
    request: Mapped["Request"] = relationship(back_populates="clarifications")
    asker: Mapped["User"] = relationship(back_populates="clarifications_asked")