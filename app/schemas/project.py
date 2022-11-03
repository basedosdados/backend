# -*- coding: utf-8 -*-
from pydantic import BaseModel


class ProjectBase(BaseModel):
    id: int
    name: str


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(ProjectBase):
    pass


class ProjectInDBBase(ProjectBase):
    class Config:
        orm_mode = True


class Project(ProjectInDBBase):
    pass


class ProjectInDB(ProjectInDBBase):
    pass
