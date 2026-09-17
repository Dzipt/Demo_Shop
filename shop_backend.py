from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal, ROUND_HALF_UP
from itertools import count

import requests


MONEY = Decimal("0.01")


@dataclass(frozen=True)
class Product:
    sku: str
    name: str
    brand: str
    category: str
    price: Decimal
    stock: int
    specifications: dict[str, str]


class DemoOnlineStore:
    """In-memory model of store services used by the TestOps demo suite."""

    def __init__(self) -> None:
        self.products = {
            product.sku: product
            for product in (
                Product(
                    "PHN-APPLE-15",
                    "Смартфон Apple iPhone 15 128 ГБ",
                    "Apple",
                    "Смартфоны",
                    Decimal("79990"),
                    12,
                    {"Память": "128 ГБ", "Цвет": "Чёрный", "Гарантия": "1 год"},
                ),
                Product(
                    "PHN-SAMSUNG-S24",
                    "Смартфон Samsung Galaxy S24 256 ГБ",
                    "Samsung",
                    "Смартфоны",
                    Decimal("89990"),
                    8,
                    {"Память": "256 ГБ", "Цвет": "Серый", "Гарантия": "1 год"},
                ),
                Product(
                    "PHN-XIAOMI-14",
                    "Смартфон Xiaomi 14 512 ГБ",
                    "Xiaomi",
                    "Смартфоны",
                    Decimal("64990"),
                    0,
                    {"Память": "512 ГБ", "Цвет": "Зелёный", "Гарантия": "1 год"},
                ),
                Product(
                    "LAP-APPLE-AIR13",
                    "Ноутбук Apple MacBook Air 13 M3",
                    "Apple",
                    "Ноутбуки",
                    Decimal("129990"),
                    5,
                    {"Память": "16 ГБ", "Накопитель": "512 ГБ", "Цвет": "Серый"},
                ),
                Product(
                    "LAP-LENOVO-T14",
                    "Ноутбук Lenovo ThinkPad T14 Gen 5",
                    "Lenovo",
                    "Ноутбуки",
                    Decimal("149990"),
                    4,
                    {
                        "Экран": "14 дюймов, IPS, 1920 x 1200",
                        "Процессор": "Intel Core Ultra 7 155U",
                        "Память": "32 ГБ DDR5",
                        "Накопитель": "SSD 1 ТБ",
                        "Цвет": "Чёрный",
                        "Гарантия": "3 года",
                    },
                ),
                Product(
                    "HDP-SONY-XM5",
                    "Наушники Sony WH-1000XM5",
                    "Sony",
                    "Наушники",
                    Decimal("34990"),
                    17,
                    {"Цвет": "Чёрный", "Подключение": "Bluetooth", "Гарантия": "1 год"},
                ),
                Product(
                    "HDP-APPLE-PRO2",
                    "Наушники Apple AirPods Pro 2",
                    "Apple",
                    "Наушники",
                    Decimal("24990"),
                    21,
                    {"Цвет": "Белый", "Подключение": "Bluetooth", "Гарантия": "1 год"},
                ),
                Product(
                    "ACC-CASE-XM5",
                    "Чехол для наушников Sony WH-1000XM5",
                    "Demo Accessories",
                    "Аксессуары",
                    Decimal("1990"),
                    30,
                    {"Материал": "Текстиль", "Цвет": "Чёрный"},
                ),
            )
        }
        self.orders: dict[str, dict] = {}
        self.consent_events: dict[str, dict] = {}
        self.payment_events: set[str] = set()
        self._order_numbers = count(100041)

    def search(
        self,
        query: str,
        *,
        brand: str | None = None,
        in_stock: bool = True,
    ) -> list[dict]:
        normalized_query = " ".join(query.casefold().split())
        result = []
        for product in self.products.values():
            searchable = (
                f"{product.name} {product.brand} {product.category} {product.sku}"
            ).casefold()
            if normalized_query not in searchable:
                continue
            if brand and product.brand.casefold() != brand.casefold():
                continue
            if in_stock and product.stock == 0:
                continue
            result.append(asdict(product))
        return sorted(result, key=lambda item: (item["price"], item["sku"]))

    def get_product_card(self, sku: str) -> dict:
        if sku not in self.products:
            raise ValueError(f"CATALOG-404: товар {sku} отсутствует в каталоге")
        product = self.products[sku]
        return {
            **asdict(product),
            "price": str(product.price.quantize(MONEY)),
            "galleryImages": 5,
            "published": True,
        }

    def get_product_media(self, sku: str) -> dict:
        if sku not in self.products:
            raise ValueError(f"CATALOG-404: товар {sku} отсутствует в каталоге")
        raise requests.exceptions.Timeout(
            "HTTPSConnectionPool(host='product-media.demo.internal', port=443): "
            "Read timed out after 3.0 seconds while requesting "
            f"/api/v1/products/{sku}/gallery [SHOP-837]"
        )

    def cart_summary(self, lines: list[tuple[str, int]]) -> dict:
        cart_lines = []
        subtotal = Decimal("0")
        for sku, quantity in lines:
            if sku not in self.products:
                raise ValueError(f"CATALOG-404: товар {sku} отсутствует в каталоге")
            product = self.products[sku]
            if quantity < 1:
                raise ValueError("CART-VALIDATION: количество должно быть не меньше 1")
            if quantity > product.stock:
                raise ValueError(
                    f"CART-STOCK-CONFLICT: для {sku} запрошено {quantity}, "
                    f"доступно {product.stock}"
                )
            line_total = (product.price * quantity).quantize(MONEY)
            subtotal += line_total
            cart_lines.append(
                {
                    "sku": sku,
                    "name": product.name,
                    "quantity": quantity,
                    "unitPrice": str(product.price.quantize(MONEY)),
                    "lineTotal": str(line_total),
                }
            )
        delivery = Decimal("0") if subtotal >= Decimal("100000") else Decimal("390")
        total = (subtotal + delivery).quantize(MONEY)
        return {
            "currency": "RUB",
            "lines": cart_lines,
            "subtotal": str(subtotal.quantize(MONEY)),
            "delivery": str(delivery.quantize(MONEY)),
            "total": str(total),
        }

    def apply_promocode(
        self,
        subtotal: Decimal,
        code: str,
        *,
        application_count: int = 1,
    ) -> dict:
        if code != "WELCOME10" or subtotal < Decimal("3000"):
            return {
                "code": code,
                "discount": "0.00",
                "total": str(subtotal.quantize(MONEY)),
            }

        discount_per_application = min(
            (subtotal * Decimal("0.10")).quantize(MONEY, rounding=ROUND_HALF_UP),
            Decimal("3000"),
        )
        # Known defect SHOP-487: a retry applies the same discount again.
        discount = (discount_per_application * application_count).quantize(MONEY)
        total = max(subtotal - discount, Decimal("0")).quantize(MONEY)
        return {
            "code": code,
            "discount": str(discount),
            "total": str(total),
            "applications": application_count,
        }

    def create_order(
        self,
        *,
        customer_id: str,
        lines: list[tuple[str, int]],
        delivery: str,
    ) -> dict:
        cart = self.cart_summary(lines)
        order_id = f"ORD-{next(self._order_numbers)}"
        order = {
            "id": order_id,
            "customerId": customer_id,
            "status": "Создан",
            "deliveryMethod": delivery,
            "total": cart["total"],
            "currency": cart["currency"],
            "items": cart["lines"],
            "historyIndexEvent": f"order.created:{order_id}",
            "consentAccepted": False,
        }
        self.orders[order_id] = order
        return order.copy()

    def record_consent(
        self,
        *,
        order_id: str,
        customer_id: str,
        policy_version: str,
        accepted_at: str,
    ) -> dict:
        if order_id not in self.orders:
            raise ValueError(f"ORDER-404: заказ {order_id} не найден")
        event_id = f"consent:{order_id}:{policy_version}"
        event = {
            "eventId": event_id,
            "eventType": "checkout.personal_data_consent.accepted",
            "orderId": order_id,
            "customerId": customer_id,
            "policyVersion": policy_version,
            "accepted": True,
            "acceptedAt": accepted_at,
            "channel": "web-checkout",
        }
        self.consent_events.setdefault(event_id, event)
        self.orders[order_id]["consentAccepted"] = True
        self.orders[order_id]["consentPolicyVersion"] = policy_version
        return self.consent_events[event_id].copy()

    def delivery_quote(self, city: str, address: str) -> dict:
        key = (city.casefold(), address.casefold())
        quotes = {
            ("москва", "ул. тверская д. 12"): ("A", True, 290, 1, None),
            ("москва", "ул. новомосковская д. 17"): ("B", True, 390, 1, None),
            ("химки", "ленинградское ш. д. 8"): ("C", True, 590, 2, None),
            ("казань", "ул. баумана д. 44"): ("A", True, 390, 2, None),
            ("новосибирск", "красный проспект д. 81"): ("B", True, 490, 3, None),
            (
                "норильск",
                "ленинский проспект д. 21",
            ): ("Удалённая", False, None, None, "Доставка в пункт выдачи"),
        }
        if key not in quotes:
            raise ValueError(f"DELIVERY-ADDRESS-UNKNOWN: адрес {city}, {address} не распознан")
        zone, available, price, sla_days, alternative = quotes[key]
        return {
            "city": city,
            "address": address,
            "zone": zone,
            "courierAvailable": available,
            "price": price,
            "slaDays": sla_days,
            "alternative": alternative,
        }

    def reserve_delivery_slot(self, city: str, address: str) -> dict:
        quote = self.delivery_quote(city, address)
        raise requests.exceptions.ConnectionError(
            "HTTPConnectionPool(host='delivery-slots.demo.internal', port=8080): "
            "Max retries exceeded with url: /api/v1/slots/reserve "
            f"for zone={quote['zone']} [SHOP-902]"
        )

    def process_payment_callback(self, payload: dict) -> dict:
        event_id = payload["eventId"]
        duplicate = event_id in self.payment_events
        self.payment_events.add(event_id)
        order = self.orders[payload["orderId"]]
        if not duplicate:
            order["status"] = "Оплачен"
            order["paymentId"] = payload["paymentId"]
        return {
            "httpStatus": 200,
            "processingResult": "duplicate_ignored" if duplicate else "accepted",
            "paymentRecords": 1,
            "orderStatus": order["status"],
        }

    def pay_by_card(self, *, order_id: str, payment_token: str) -> dict:
        if order_id not in self.orders:
            raise ValueError(f"ORDER-404: заказ {order_id} не найден")
        if not payment_token.startswith("tok_demo_"):
            raise ValueError("PAYMENT-TOKEN-INVALID: неизвестный формат токена")
        raise requests.exceptions.SSLError(
            "HTTPSConnectionPool(host='sandbox-payments.demo.internal', port=443): "
            "Max retries exceeded with url: /api/v2/payments "
            "(Caused by SSLError(SSLCertVerificationError(1, "
            "'[SSL: CERTIFICATE_VERIFY_FAILED] certificate has expired: "
            "notAfter=Aug 12 23:59:59 2026 GMT'))) [SHOP-503]"
        )

    def calculate_refund(
        self,
        *,
        paid_for_item: Decimal,
        delivery_paid: Decimal,
        delivery_was_completed: bool,
    ) -> dict:
        # Known defect SHOP-619: completed delivery is incorrectly refunded.
        delivery_refund = delivery_paid if delivery_was_completed else delivery_paid
        total = (paid_for_item + delivery_refund).quantize(MONEY)
        return {
            "itemRefund": str(paid_for_item.quantize(MONEY)),
            "deliveryRefund": str(delivery_refund.quantize(MONEY)),
            "totalRefund": str(total),
        }
