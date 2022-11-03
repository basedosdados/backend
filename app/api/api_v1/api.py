# -*- coding: utf-8 -*-
"""
Version 1 API index
"""

from fastapi import APIRouter

from app.api.api_v1.endpoints import category

api_router = APIRouter()
api_router.include_router(category.router, prefix="/category", tags=["category"])
