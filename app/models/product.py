from decimal import Decimal

from uuid import uuid4

from sqlalchemy import ForeignKey, Integer, JSON, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    sku: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), index=True
    )
    attributes: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)

    category: Mapped["Category | None"] = relationship(back_populates="products")
    cart_items: Mapped[list["CartItem"]] = relationship(back_populates="product")
