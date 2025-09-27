from __future__ import annotations

from datetime import date, datetime
from typing import Optional

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