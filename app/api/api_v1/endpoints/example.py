# -*- coding: utf-8 -*-
"""
Example endpoints
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def example():
    """
    Example endpoint
    """
    return {"message": "Hello World"}
