# -*- coding: utf-8 -*-
from typing import List

from pydantic import BaseModel, ValidationError, validator

from app.schemas.category import Category
from app.schemas.dataset import Dataset
from app.schemas.tag import Tag


class Table(BaseModel):
    id: int
    name: str
    short_description: str
    long_description: str
    update_frequency: str
    temporal_coverage: str
    data_owner: str
    publisher_name: str
    publisher_email: str
    source_database: str
    source_table: str
    source_query: str
    tags: List[Tag]
    categories: List[Category]
    dataset: Dataset

    # Validate that the table's name is unique within the dataset
    @validator("name")
    def name_is_unique_within_dataset(cls, v, values):
        if v in [table.name for table in values["dataset"].tables]:
            raise ValidationError("Table name must be unique within dataset")
        return v
