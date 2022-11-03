# -*- coding: utf-8 -*-
from pydantic import BaseModel


class Tag(BaseModel):
    id: int
    name: str
