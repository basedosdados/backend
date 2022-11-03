# -*- coding: utf-8 -*-
from pydantic import BaseModel


class CategoryBase(BaseModel):
    id: int
    name: str
    path: str


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(CategoryBase):
    pass


class CategoryInDBBase(CategoryBase):
    class Config:
        orm_mode = True


class Category(CategoryInDBBase):
    pass


class CategoryInDB(CategoryInDBBase):
    pass
