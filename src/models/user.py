# src/models/user.py
from sqlalchemy import String, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from src.models import Base

class User(Base):
    __tablename__ = "users"

    max_user_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    consent_given: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_version: Mapped[str] = mapped_column(String(50), nullable=True)
    consent_timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    role: Mapped[str] = mapped_column(String(50), default="user")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    # Связи (используем строку для отложенной загрузки)
    requests: Mapped[list["Request"]] = relationship(back_populates="initiator")