from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from config import settings
import datetime

Base = declarative_base()

class Conversation(Base):
    __tablename__ = 'conversations'
    id = Column(Integer, primary_key=True)
    user_query = Column(Text)
    bot_response = Column(Text)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

class DatabaseManager:
    def __init__(self):
        self.engine = create_engine(settings.DATABASE_URL)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def add_conversation(self, user_query, bot_response):
        session = self.Session()
        convo = Conversation(user_query=user_query, bot_response=bot_response)
        session.add(convo)
        session.commit()
        session.close()

    def get_history(self, limit=20):
        session = self.Session()
        history = session.query(Conversation).order_by(Conversation.timestamp.desc()).limit(limit).all()
        session.close()
        return history

    def delete_conversation(self, conv_id: int) -> bool:
        session = self.Session()
        try:
            obj = session.query(Conversation).filter(Conversation.id == conv_id).one_or_none()
            if not obj:
                session.close()
                return False
            session.delete(obj)
            session.commit()
            session.close()
            return True
        except Exception:
            session.rollback()
            session.close()
            return False

    def clear_history(self) -> int:
        session = self.Session()
        try:
            count = session.query(Conversation).delete()
            session.commit()
            session.close()
            return int(count or 0)
        except Exception:
            session.rollback()
            session.close()
            return 0
