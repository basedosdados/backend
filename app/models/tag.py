# -*- coding: utf-8 -*-
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from app.database.base_class import Base


class Tag(Base):
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True)
    tables = relationship("Table", secondary="table_tag")
