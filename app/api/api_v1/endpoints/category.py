# -*- coding: utf-8 -*-
"""
CRUD endpoints for Category model.
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.future import select
from sqlalchemy.orm import Session

from app.database.session import get_session
from app.models import Category, CategoryCreate, CategoryUpdate

router = APIRouter()


@router.get("/", response_model=List[Category])
async def read_categories(
    session: Session = Depends(get_session),
) -> List[Category]:
    """
    Retrieve categories.
    """
    result = await session.execute(select(Category))
    categories = result.scalars().all()
    return categories


@router.post("/", response_model=Category, status_code=status.HTTP_201_CREATED)
async def create_category(
    *,
    session: Session = Depends(get_session),
    category_in: CategoryCreate,
) -> Category:
    """
    Create new category.
    """
    category = Category(**category_in.dict())
    session.add(category)
    await session.commit()
    await session.refresh(category)
    return category


@router.get("/{category_id}", response_model=Category)
async def read_category(
    *,
    session: Session = Depends(get_session),
    category_id: int,
) -> Category:
    """
    Get category by ID.
    """
    result = await session.execute(select(Category).where(Category.id == category_id))
    category = result.scalar_one_or_none()
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )
    return category


@router.put("/{category_id}", response_model=Category)
async def update_category(
    *,
    session: Session = Depends(get_session),
    category_id: int,
    category_in: CategoryUpdate,
) -> Category:
    """
    Update an category.
    """
    result = await session.execute(select(Category).where(Category.id == category_id))
    category = result.scalar_one_or_none()
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )
    category_data = category_in.dict(exclude_unset=True)
    for field in category_data:
        setattr(category, field, category_data[field])
    session.add(category)
    await session.commit()
    await session.refresh(category)
    return category


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    *,
    session: Session = Depends(get_session),
    category_id: int,
) -> None:
    """
    Delete an category.
    """
    result = await session.execute(select(Category).where(Category.id == category_id))
    category = result.scalar_one_or_none()
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )
    session.delete(category)
    await session.commit()
