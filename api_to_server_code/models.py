import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship

from database import Base, engine


class Users(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String)  # Just for keeping track of who is this user
    token = Column(String)  # Should be mangled for security
    requests_done = Column(Integer)
    requests_available = Column(Integer, nullable=True)
    pool = Column(Integer)

    def can_do_requests(self) -> bool:
        if self.requests_available is None:
            return True
        return self.requests_done < self.requests_available


class Entries(Base):
    __tablename__ = "entries"

    id = Column(Integer, primary_key=True, index=True)
    submitted_by_id = Column(Integer, ForeignKey(Users.id), nullable=True)
    sku = Column(Integer)
    link = Column(String)
    query = Column(String)
    toloka_task_id = Column(String, nullable=True)
    ans = Column(ARRAY(Integer, dimensions=1), nullable=True)
    overlap = Column(Integer, nullable=True)
    remaining_overlap = Column(Integer, nullable=True)
    count_tasksik = Column(Integer, nullable=True)
    res = Column(Integer, nullable=True)
    is_more = Column(Boolean, nullable=True)
    pool_id = Column(Integer, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    status = Column(String)

    submitted_by = relationship('Users', foreign_keys="Entries.submitted_by_id")


Base.metadata.create_all(engine)
Base.metadata.create_all(engine)