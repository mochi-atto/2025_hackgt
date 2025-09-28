from __future__ import annotations

from datetime import date, datetime
from typing import Optional
from enum import Enum

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Support both package and script execution
try:
    from .db import Base
except ImportError:  # running as a script
    import os, sys
    sys.path.append(os.path.dirname(__file__))
    from db import Base


class FoodItem(Base):
    __tablename__ = "food_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    brand: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    category: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    upc: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, unique=False, index=True)
    is_perishable: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    nutrition: Mapped["NutritionFacts"] = relationship(
        back_populates="food_item", uselist=False, cascade="all, delete-orphan"
    )
    inventory_items: Mapped[list["InventoryItem"]] = relationship(back_populates="food_item")

    __table_args__ = (
        # Avoid exact duplicates of the same item/brand/upc
        UniqueConstraint("name", "brand", "upc", name="uq_food_name_brand_upc"),
    )


class NutritionFacts(Base):
    __tablename__ = "nutrition_facts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    food_item_id: Mapped[int] = mapped_column(ForeignKey("food_items.id", ondelete="CASCADE"), unique=True)

    serving_size: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    serving_unit: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    calories: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    protein_g: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    carbs_g: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    fat_g: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    fiber_g: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sugar_g: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sodium_mg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    food_item: Mapped[FoodItem] = relationship(back_populates="nutrition")


class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    food_item_id: Mapped[int] = mapped_column(ForeignKey("food_items.id", ondelete="CASCADE"), index=True)

    quantity: Mapped[float] = mapped_column(Float, default=1.0)
    unit: Mapped[str] = mapped_column(String(32), default="unit")

    expiry_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    opened_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Optional: track a household/user later
    household_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    food_item: Mapped[FoodItem] = relationship(back_populates="inventory_items")

    __table_args__ = (
        CheckConstraint("quantity >= 0", name="ck_quantity_nonnegative"),
    )


class CustomFood(Base):
    """User-created custom foods like leftovers, homemade items, etc."""
    __tablename__ = "custom_foods"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    
    # Nutrition info (user provided or AI estimated)
    serving_size: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    serving_unit: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, default="serving")
    
    calories: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    protein_g: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    carbs_g: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    fat_g: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    fiber_g: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sugar_g: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Track if nutrition was AI estimated vs user provided
    nutrition_estimated: Mapped[bool] = mapped_column(Boolean, default=False)
    estimated_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0-1 confidence
    
    # User/household association
    user_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    grocery_items: Mapped[list["UserGrocery"]] = relationship(back_populates="custom_food")


class UserGrocery(Base):
    """User's current grocery inventory with expiration tracking"""
    __tablename__ = "user_groceries"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    # Reference either USDA food item OR custom food
    food_item_id: Mapped[Optional[int]] = mapped_column(ForeignKey("food_items.id", ondelete="CASCADE"), nullable=True, index=True)
    custom_food_id: Mapped[Optional[int]] = mapped_column(ForeignKey("custom_foods.id", ondelete="CASCADE"), nullable=True, index=True)
    
    # User/household identification
    user_id: Mapped[str] = mapped_column(String(128), index=True)  # Required for grocery tracking
    
    # Quantity and location info
    quantity: Mapped[float] = mapped_column(Float, default=1.0)
    unit: Mapped[str] = mapped_column(String(32), default="unit")
    location: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)  # "fridge", "pantry", "freezer"
    
    # Date tracking
    purchase_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    expiration_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    opened_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    # Status tracking
    is_opened: Mapped[bool] = mapped_column(Boolean, default=False)
    is_expired: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    food_item: Mapped[Optional[FoodItem]] = relationship()
    custom_food: Mapped[Optional[CustomFood]] = relationship(back_populates="grocery_items")
    
    __table_args__ = (
        CheckConstraint("quantity >= 0", name="ck_grocery_quantity_nonnegative"),
        # Must reference either USDA food OR custom food, not both
        CheckConstraint(
            "(food_item_id IS NOT NULL AND custom_food_id IS NULL) OR (food_item_id IS NULL AND custom_food_id IS NOT NULL)", 
            name="ck_food_reference"
        ),
    )


class UserFavorite(Base):
    """User favorites for frequently used ingredients (USDA items or custom foods)."""
    __tablename__ = "user_favorites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128), index=True)

    # Reference either USDA food item OR custom food (one-of)
    food_item_id: Mapped[Optional[int]] = mapped_column(ForeignKey("food_items.id", ondelete="CASCADE"), nullable=True, index=True)
    custom_food_id: Mapped[Optional[int]] = mapped_column(ForeignKey("custom_foods.id", ondelete="CASCADE"), nullable=True, index=True)

    display_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    food_item: Mapped[Optional[FoodItem]] = relationship()
    custom_food: Mapped[Optional[CustomFood]] = relationship()

    __table_args__ = (
        # Enforce one-of semantics
        CheckConstraint(
            "(food_item_id IS NOT NULL AND custom_food_id IS NULL) OR (food_item_id IS NULL AND custom_food_id IS NOT NULL)",
            name="ck_favorite_reference_oneof",
        ),
        # Prevent duplicates per user per referenced item
        UniqueConstraint("user_id", "food_item_id", name="uq_fav_user_fooditem"),
        UniqueConstraint("user_id", "custom_food_id", name="uq_fav_user_customfood"),
    )
