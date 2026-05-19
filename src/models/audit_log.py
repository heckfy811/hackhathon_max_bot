from sqlalchemy import String, DateTime, Text, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from src.models import Base

class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    request_id: Mapped[str] = mapped_column(String(36), ForeignKey("bot_schema.requests.id"))
    action: Mapped[str] = mapped_column(String(100))
    actor_id: Mapped[str] = mapped_column(String(255))
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    details: Mapped[str] = mapped_column(Text, nullable=True)

    # Связи (используем строку для отложенной загрузки)
    request: Mapped["Request"] = relationship(back_populates="audit_logs")