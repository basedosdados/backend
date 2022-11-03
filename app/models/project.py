# -*- coding: utf-8 -*-
from sqlalchemy import Column, Integer, String

from app.database.base_class import Base


class Project(Base):
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True)
