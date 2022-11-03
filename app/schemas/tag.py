# -*- coding: utf-8 -*-
from pydantic import BaseModel


class TagBase(BaseModel):
    id: int
    name: str


class TagCreate(TagBase):
    pass


class TagUpdate(TagBase):
    pass


class TagInDBBase(TagBase):
    class Config:
        orm_mode = True


class Tag(TagInDBBase):
    pass


class TagInDB(TagInDBBase):
    pass
