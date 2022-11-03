# -*- coding: utf-8 -*-
from pydantic import BaseModel, ValidationError, validator

from app.schemas.table import Table


class Column(BaseModel):
    id: int
    original_name: str
    name: str
    data_type: str
    description: str
    is_sensitive: bool
    temporal_coverage: str
    measurement_unit: str
    contains_dict: bool
    comments: str
    table: Table

    # Validate that the column's name is unique within the table
    @validator("name")
    def name_is_unique_within_table(cls, v, values):
        if v in [column.name for column in values["table"].columns]:
            raise ValidationError("Column name must be unique within table")
        return v


class ColumnInDB(Column):
    class Config:
        orm_mode = True
