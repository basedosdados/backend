# -*- coding: utf-8 -*-
from sqlalchemy import Boolean, Column, Integer, String
from sqlalchemy.orm import relationship

from app.database.base_class import Base


class Column(Base):
    id = Column(Integer, primary_key=True, index=True)
    original_name = Column(String(100), unique=True, index=True)
    name = Column(String(100), unique=True, index=True)
    data_type = Column(String(100))
    description = Column(String(1000))
    is_sensitive = Column(Boolean)
    temporal_coverage = Column(String(100))
    measurement_unit = Column(String(100))
    contains_dict = Column(Boolean)
    comments = Column(String(1000))
    table = relationship("Table", back_populates="columns")
