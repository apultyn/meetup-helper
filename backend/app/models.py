from datetime import datetime

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from .database import Base


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(12), unique=True, index=True, nullable=False)
    name = Column(String(160), nullable=False)
    description = Column(Text, nullable=False, default="")
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    duration_days = Column(Integer, nullable=False)
    created_by = Column(String(80), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    participants = relationship("Participant", back_populates="event", cascade="all, delete-orphan")
    blockers = relationship("Blocker", back_populates="event", cascade="all, delete-orphan")
    logs = relationship("OperationLog", back_populates="event", cascade="all, delete-orphan")


class Participant(Base):
    __tablename__ = "participants"
    __table_args__ = (UniqueConstraint("event_id", "login_key", name="uq_participant_event_login"),)

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    login = Column(String(80), nullable=False)
    login_key = Column(String(80), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    event = relationship("Event", back_populates="participants")
    blockers = relationship("Blocker", back_populates="participant", cascade="all, delete-orphan")


class Blocker(Base):
    __tablename__ = "blockers"
    __table_args__ = (UniqueConstraint("participant_id", "date", name="uq_blocker_participant_date"),)

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    participant_id = Column(Integer, ForeignKey("participants.id"), nullable=False)
    date = Column(Date, nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    event = relationship("Event", back_populates="blockers")
    participant = relationship("Participant", back_populates="blockers")


class OperationLog(Base):
    __tablename__ = "operation_logs"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True)
    actor = Column(String(80), nullable=False)
    action = Column(String(80), nullable=False)
    details = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    event = relationship("Event", back_populates="logs")

