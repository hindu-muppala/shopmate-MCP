from pydantic import BaseModel

from app.schemas.order import OrderRead


class CheckoutRead(BaseModel):
    order: OrderRead
