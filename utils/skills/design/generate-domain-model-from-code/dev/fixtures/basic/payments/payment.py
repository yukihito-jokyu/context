from dataclasses import dataclass
from sales.order import Order


@dataclass
class Payment:
    order: Order
    amount: int
