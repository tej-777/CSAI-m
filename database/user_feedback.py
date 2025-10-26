from sqlalchemy import create_engine, Column, Integer, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from config import settings
import datetime

Base = declarative_base()

class UserFeedback(Base):
    __tablename__ = 'user_feedback'
    id = Column(Integer, primary_key=True)
    feedback = Column(Text)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

class FeedbackManager:
    def __init__(self):
        self.engine = create_engine(settings.DATABASE_URL)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def add_feedback(self, feedback_text):
        session = self.Session()
        feedback = UserFeedback(feedback=feedback_text)
        session.add(feedback)
        session.commit()
        session.close()

    def get_feedback(self, limit=20):
        session = self.Session()
        feedbacks = session.query(UserFeedback).order_by(UserFeedback.timestamp.desc()).limit(limit).all()
        session.close()
        return feedbacks
