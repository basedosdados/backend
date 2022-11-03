# -*- coding: utf-8 -*-
from pydantic import BaseModel


class Project(BaseModel):
    id: int
    name: str


class ProjectInDB(Project):
    class Config:
        orm_mode = True
