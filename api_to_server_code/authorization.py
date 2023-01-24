from sqlalchemy.orm import Session
from models import Users

def authorize(db: Session, token: str) -> Users:
    return db.query(Users).filter(Users.token == token).first()