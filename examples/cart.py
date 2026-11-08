"""Runnable nested cart example; no dependency on Kafka/Redis/SQL.

Run: python examples/cart.py (after pip install -e .)
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from redmud import Processor, Rule, Runtime, Settings


@dataclass(frozen=True, slots=True)
class Item:
    product_id: int
    price_minor: int
    quantity: int
    discount_pct: int


@dataclass(frozen=True, slots=True)
class Order:
    order_id: int
    items: tuple[Item, ...]


@dataclass(frozen=True, slots=True)
class Cart:
    cart_id: int
    customer_id: int
    promo_pct: int
    delivery_minor: int
    orders: tuple[Order, ...]


def cart_is_valid(cart: Cart) -> bool:
    return bool(cart.orders) and all(
        order.items and all(
            item.price_minor >= 0 and item.quantity > 0 and
            0 <= item.discount_pct <= 100
            for item in order.items
        ) for order in cart.orders
    ) and 0 <= cart.promo_pct <= 100 and cart.delivery_minor >= 0


class CartTransform(Processor[Cart, dict[str, Any]]):
    def parse(self, raw: Any) -> Cart:
        data = super().parse(raw)
        return Cart(
            cart_id=int(data["cart_id"]),
            customer_id=int(data["customer_id"]),
            promo_pct=int(data.get("promo_pct", 0)),
            delivery_minor=int(data.get("delivery_minor", 0)),
            orders=tuple(
                Order(
                    order_id=int(order["order_id"]),
                    items=tuple(Item(
                        product_id=int(item["product_id"]),
                        price_minor=int(item["price_minor"]),
                        quantity=int(item["quantity"]),
                        discount_pct=int(item.get("discount_pct", 0)),
                    ) for item in order["items"]),
                ) for order in data["orders"]
            ),
        )

    def input_rules(self):
        return (Rule("valid_cart", cart_is_valid, message="Cart contains invalid items"),)

    def output_rules(self):
        return (
            Rule("nonnegative_total", lambda r: r["total_minor"] >= 0),
            Rule("very_large_cart", lambda r: r["total_minor"] < 10_000_000,
                 severity="warn", message="Unusually large cart"),
        )

    def transform(self, cart: Cart) -> dict[str, Any]:
        # All money is integer minor units. Integer division is applied per item.
        orders = []
        for order in cart.orders:
            total = sum(
                item.price_minor * item.quantity * (100 - item.discount_pct) // 100
                for item in order.items
            )
            orders.append({"order_id": order.order_id, "total_minor": total})
        subtotal = sum(x["total_minor"] for x in orders)
        promo = subtotal * cart.promo_pct // 100
        return {
            "cart_id": cart.cart_id,
            "customer_id": cart.customer_id,
            "subtotal_minor": subtotal,
            "promo_minor": promo,
            "total_minor": subtotal - promo + cart.delivery_minor,
            "order_totals": orders,
        }


def sample(cart_id: int = 5001) -> bytes:
    return json.dumps({
        "cart_id": cart_id,
        "customer_id": 777,
        "promo_pct": 10,
        "delivery_minor": 1500,
        "orders": [
            {"order_id": 101, "items": [
                {"product_id": 1, "price_minor": 300000, "quantity": 1, "discount_pct": 5},
                {"product_id": 2, "price_minor": 10000, "quantity": 2, "discount_pct": 0},
            ]},
            {"order_id": 102, "items": [
                {"product_id": 3, "price_minor": 100000, "quantity": 1, "discount_pct": 10},
            ]},
        ],
    }).encode()


if __name__ == "__main__":
    runtime = Runtime(
        CartTransform(),
        Settings(batch_size=128, timing_sample_every=1,
                 output_fields=("total_minor", "subtotal_minor")),
    )
    # Any Iterable[bytes|dict|object] from any upstream system can be supplied.
    incoming = [sample(5001), sample(5002), b'{invalid json}', sample(5003)]
    for record in runtime.process_iter(incoming):
        print(f"status={record.status} index={record.index} value={record.value}")
        if record.issues:
            print("quality issues:", record.issues)
        if record.error_stage:
            print("error:", record.error_stage, record.error_type)
    print(json.dumps(runtime.snapshot(), indent=2, ensure_ascii=False))
    print(runtime.metrics.prometheus_text())
