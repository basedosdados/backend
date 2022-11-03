# -*- coding: utf-8 -*-
from pydantic import BaseModel


class Category(BaseModel):
    id: int
    name: str
    path: str
