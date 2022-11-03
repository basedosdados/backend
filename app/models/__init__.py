# -*- coding: utf-8 -*-
from typing import List, Optional

from pydantic import ValidationError, validator
from sqlmodel import Field, Relationship, SQLModel


class TableCategoryLink(SQLModel):
    table_id: Optional[int] = Field(
        default=None, foreign_key="table.id", primary_key=True
    )
    category_id: Optional[int] = Field(
        default=None, foreign_key="category.id", primary_key=True
    )


class TableTagLink(SQLModel):
    table_id: Optional[int] = Field(
        default=None, foreign_key="table.id", primary_key=True
    )
    tag_id: Optional[int] = Field(default=None, foreign_key="tag.id", primary_key=True)


class CategoryBase(SQLModel):
    name: str
    path: str

    tables: List["Table"] = Relationship(
        back_populates="categories", link_model=TableCategoryLink
    )


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(CategoryBase):
    pass


class Category(CategoryBase, table=True):
    id: int = Field(default=None, primary_key=True)


class TagBase(SQLModel):
    name: str

    tables: List["Table"] = Relationship(back_populates="tags", link_model=TableTagLink)


class TagCreate(TagBase):
    pass


class TagUpdate(TagBase):
    pass


class Tag(TagBase, table=True):
    id: int = Field(default=None, primary_key=True)


class ProjectBase(SQLModel):
    name: str

    datasets: List["Dataset"] = Relationship(back_populates="project")


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(ProjectBase):
    pass


class Project(ProjectBase, table=True):
    id: int = Field(default=None, primary_key=True)


class DatasetBase(SQLModel):
    name: str
    title_prefix: str

    project_id: int = Field(default=None, foreign_key="project.id")
    project: "Project" = Relationship(back_populates="datasets")
    tables: List["Table"] = Relationship(back_populates="dataset")

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


class Dataset(DatasetBase, table=True):
    id: int = Field(default=None, primary_key=True)


class TableBase(SQLModel):
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

    tags: List["Tag"] = Relationship(back_populates="tables", link_model=TableTagLink)
    categories: List["Category"] = Relationship(
        back_populates="tables", link_model=TableCategoryLink
    )
    dataset_id: int = Field(default=None, foreign_key="dataset.id")
    dataset: "Dataset" = Relationship(back_populates="tables")
    columns: List["Column"] = Relationship(back_populates="table")

    # Validate that the table's name is unique within the dataset
    @validator("name")
    def name_is_unique_within_dataset(cls, v, values):
        if v in [table.name for table in values["dataset"].tables]:
            raise ValidationError("Table name must be unique within dataset")
        return v


class TableCreate(TableBase):
    pass


class TableUpdate(TableBase):
    pass


class Table(TableBase, table=True):
    id: int = Field(default=None, primary_key=True)


class ColumnBase(SQLModel):
    original_name: str
    name: str
    data_type: str
    description: str
    is_sensitive: bool
    temporal_coverage: str
    measurement_unit: str
    contains_dict: bool
    comments: str

    table_id: int = Field(default=None, foreign_key="table.id")
    table: "Table" = Relationship(back_populates="columns")

    # Validate that the column's name is unique within the table
    @validator("name")
    def name_is_unique_within_table(cls, v, values):
        if v in [column.name for column in values["table"].columns]:
            raise ValidationError("Column name must be unique within table")
        return v


class ColumnCreate(ColumnBase):
    pass


class ColumnUpdate(ColumnBase):
    pass


class Column(ColumnBase, table=True):
    id: int = Field(default=None, primary_key=True)
