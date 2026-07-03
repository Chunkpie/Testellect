from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


from app.db.models.auth import *
from app.db.models.assessments import *
from app.db.models.mcq_engine import *
