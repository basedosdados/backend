# -*- coding: utf-8 -*-
from pydantic import BaseModel


class Project(BaseModel):
    id: int
    name: str
