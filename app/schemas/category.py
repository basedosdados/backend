# -*- coding: utf-8 -*-
from pydantic import BaseModel


class Category(BaseModel):
    id: int
    name: str
    path: str


class CategoryInDB(Category):
    class Config:
        orm_mode = True
