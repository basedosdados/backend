# -*- coding: utf-8 -*-
from app.crud.base import CRUDBase
from app.models.column import Column
from app.schemas.column import ColumnCreate, ColumnUpdate


class CRUDColumn(CRUDBase[Column, ColumnCreate, ColumnUpdate]):
    pass


column = CRUDColumn(Column)
