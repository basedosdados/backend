# -*- coding: utf-8 -*-
from app.crud.base import CRUDBase
from app.models.table import Table
from app.schemas.table import TableCreate, TableUpdate


class CRUDTable(CRUDBase[Table, TableCreate, TableUpdate]):
    pass


table = CRUDTable(Table)
