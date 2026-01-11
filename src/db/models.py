"""SQLAlchemy ORM models."""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime

from .session import Base


class User(Base):
    """User model."""
    __tablename__ = "users"

    telegram_id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), nullable=True)
    child_names = Column(Text, nullable=True)
    age = Column(String(50), nullable=True)
    traits = Column(Text, nullable=True)
    context_active = Column(Text, nullable=True)
    wishes = Column(Text, nullable=True)
    feedback = Column(Text, nullable=True)
    story_total = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    stories = relationship("Story", back_populates="user", cascade="all, delete-orphan")
    contexts = relationship("Context", back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        Index('ix_users_telegram_id', 'telegram_id', unique=True),
    )

    def to_dict(self):
        """Convert user to dictionary."""
        return {
            'user_id': str(self.telegram_id),
            'telegram_id': self.telegram_id,
            'username': self.username or '',
            'child_names': self.child_names or '',
            'age': self.age or '',
            'traits': self.traits or '',
            'context_active': self.context_active or '',
            'wishes': self.wishes or '',
            'feedback': self.feedback or '',
            'story_total': self.story_total,
            'created_at': self.created_at.isoformat() if self.created_at else '',
            'updated_at': self.updated_at.isoformat() if self.updated_at else '',
        }


class Story(Base):
    """Story model."""
    __tablename__ = "stories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.telegram_id", ondelete="CASCADE"), nullable=False, index=True)
    text = Column(Text, nullable=False)
    model = Column(String(50), default='deepseek', nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    user = relationship("User", back_populates="stories")

    __table_args__ = (
        Index('ix_stories_user_created', 'user_id', 'created_at'),
    )


class Context(Base):
    """Context model."""
    __tablename__ = "contexts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.telegram_id", ondelete="CASCADE"), nullable=False, index=True)
    kind = Column(String(20), nullable=False, index=True)  # 'active' or 'archived'
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    user = relationship("User", back_populates="contexts")

    __table_args__ = (
        Index('ix_contexts_user_kind_created', 'user_id', 'kind', 'created_at'),
    )

