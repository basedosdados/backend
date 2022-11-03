# -*- coding: utf-8 -*-
from pydantic import BaseModel, ValidationError, validator

from app.schemas.project import Project


class DatasetBase(BaseModel):
    id: int
    name: str
    title_prefix: str
    project: Project

    # Validate that the dataset's name is unique within the project
    @validator("name")
    def name_is_unique_within_project(cls, v, values):
        if v in [dataset.name for dataset in values["project"].datasets]:
            raise ValidationError("Dataset name must be unique within project")
        return v


class DatasetCreate(DatasetBase):
    pass


class DatasetUpdate(DatasetBase):
    pass


class DatasetInDBBase(DatasetBase):
    class Config:
        orm_mode = True


class Dataset(DatasetInDBBase):
    pass


class DatasetInDB(DatasetInDBBase):
    pass
