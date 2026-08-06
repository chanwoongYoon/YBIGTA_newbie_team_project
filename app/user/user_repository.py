from typing import Optional

from app.user.user_schema import User
from app.config import USER_DATA

from sqlalchemy import Column, String
from sqlalchemy.orm import declarative_base, Session

BASE = declarative_base()

class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_user_by_email(self, email: str) -> Optional[User]:
        user = self.db.query(UserORM).filter(UserORM.email == email).first()
        return User(email=user.email, password=user.password, username=user.username) if user else None

    def save_user(self, user: User) -> User: 
        existing = self.db.query(UserORM).filter(UserORM.email == user.email).first()

        if existing:
            existing.password = user.password
            existing.username = user.username
        else:
            new_user = UserORM(email=user.email, password=user.password, username=user.username)
            self.db.add(new_user)

        self.db.commit()
        return user
            
    def delete_user(self, user: User) -> User:
        del_user = self.db.query(UserORM).filter(UserORM.email == user.email).first()
        self.db.delete(del_user)
        self.db.commit()
        return user

class UserORM(BASE):
    __tablename__ = "users"
    email = Column(String(255), primary_key=True)
    password = Column(String(255), nullable=False)
    username = Column(String(255), nullable=False)