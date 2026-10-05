class ShopMateError(Exception):
    """Base class for expected application errors."""


class InvalidRequest(ShopMateError):
    pass


class ProductNotFound(ShopMateError):
    pass


class InsufficientStock(ShopMateError):
    pass


class CartNotFound(ShopMateError):
    pass


class OrderNotFound(ShopMateError):
    pass


class InvalidOrderTransition(ShopMateError):
    pass
