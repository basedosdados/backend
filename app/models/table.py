# -*- coding: utf-8 -*-
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from app.database.base_class import Base


class Table(Base):
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True)
    short_description = Column(String(100))
    long_description = Column(String(1000))
    update_frequency = Column(String(100))
    temporal_coverage = Column(String(100))
    data_owner = Column(String(100))
    publisher_name = Column(String(100))
    publisher_email = Column(String(100))
    source_database = Column(String(100))
    source_table = Column(String(100))
    source_query = Column(String(1000))
    tags = relationship("Tag", secondary="table_tag")
    categories = relationship("Category", secondary="table_category")
    dataset = relationship("Dataset", back_populates="tables")
