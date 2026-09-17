from decimal import Decimal

import allure
import pytest

from helpers import attach_json, test_case as allure_case


pytestmark = [pytest.mark.testops_demo]


@pytest.mark.api
@pytest.mark.smoke
@allure_case(
    "AUTO-SHOP-030",
    "Корзина рассчитывает стоимость одной позиции",
    "Проверяет базовый расчёт количества, стоимости строки и итога корзины.",
    feature="Корзина",
    story="Управление товарами",
    severity=allure.severity_level.BLOCKER,
    owner="Команда заказа",
    component="cart-pricing-service",
    layer="api",
    tags=("cart", "pricing", "smoke"),
)
def test_single_item_cart_total(shop, run_context):
    with allure.step("Добавить две пары наушников"):
        cart = shop.cart_summary([("HDP-APPLE-PRO2", 2)])
        attach_json("Корзина", cart)

    with allure.step("Проверить стоимость строки и итог"):
        assert cart["lines"][0]["lineTotal"] == "49980.00"
        assert cart["total"] == "50370.00"


@pytest.mark.api
@pytest.mark.regression
@allure_case(
    "AUTO-SHOP-031",
    "Доставка бесплатна при сумме от ста тысяч рублей",
    "Проверяет бизнес-порог бесплатной доставки для крупного заказа.",
    feature="Корзина",
    story="Цена и промокоды",
    severity=allure.severity_level.CRITICAL,
    owner="Команда заказа",
    component="cart-pricing-service",
    layer="api",
    tags=("cart", "delivery", "pricing"),
)
def test_delivery_is_free_above_threshold(shop, run_context):
    with allure.step("Сформировать корзину выше порога"):
        cart = shop.cart_summary([("LAP-APPLE-AIR13", 1)])

    with allure.step("Проверить стоимость доставки"):
        assert cart["subtotal"] == "129990.00"
        assert cart["delivery"] == "0.00"
        assert cart["total"] == cart["subtotal"]


@pytest.mark.api
@pytest.mark.regression
@allure_case(
    "AUTO-SHOP-032",
    "Доставка добавляется к заказу ниже порога",
    "Проверяет применение стандартного тарифа доставки к небольшой корзине.",
    feature="Корзина",
    story="Цена и промокоды",
    severity=allure.severity_level.CRITICAL,
    owner="Команда заказа",
    component="cart-pricing-service",
    layer="api",
    tags=("cart", "delivery", "pricing"),
)
def test_standard_delivery_is_added_below_threshold(shop, run_context):
    with allure.step("Добавить недорогой аксессуар"):
        cart = shop.cart_summary([("ACC-CASE-XM5", 1)])

    with allure.step("Проверить тариф и итог"):
        assert cart["delivery"] == "390.00"
        assert cart["total"] == "2380.00"


@pytest.mark.api
@pytest.mark.regression
@allure_case(
    "AUTO-SHOP-033",
    "Стоимость строки учитывает количество товара",
    "Проверяет умножение цены товара на выбранное покупателем количество.",
    feature="Корзина",
    story="Управление товарами",
    severity=allure.severity_level.CRITICAL,
    owner="Команда заказа",
    component="cart-pricing-service",
    layer="api",
    tags=("cart", "quantity"),
)
def test_line_total_uses_selected_quantity(shop, run_context):
    with allure.step("Добавить три аксессуара"):
        cart = shop.cart_summary([("ACC-CASE-XM5", 3)])

    with allure.step("Проверить количество и сумму строки"):
        line = cart["lines"][0]
        assert line["quantity"] == 3
        assert line["unitPrice"] == "1990.00"
        assert line["lineTotal"] == "5970.00"


@pytest.mark.api
@pytest.mark.regression
@allure_case(
    "AUTO-SHOP-034",
    "Корзина сохраняет выбранные SKU",
    "Проверяет состав корзины после добавления товаров из разных категорий.",
    feature="Корзина",
    story="Управление товарами",
    severity=allure.severity_level.CRITICAL,
    owner="Команда заказа",
    component="cart-service",
    layer="api",
    tags=("cart", "items"),
)
def test_cart_preserves_selected_skus(shop, run_context):
    selected = [("PHN-APPLE-15", 1), ("ACC-CASE-XM5", 1)]
    with allure.step("Добавить два товара"):
        cart = shop.cart_summary(selected)
        attach_json("Состав корзины", cart["lines"])

    with allure.step("Проверить SKU"):
        assert [line["sku"] for line in cart["lines"]] == [sku for sku, _ in selected]


@pytest.mark.api
@pytest.mark.regression
@allure_case(
    "AUTO-SHOP-035",
    "Количество товара не может быть равно нулю",
    "Проверяет серверную валидацию нулевого количества в корзине.",
    feature="Корзина",
    story="Управление товарами",
    severity=allure.severity_level.CRITICAL,
    owner="Команда заказа",
    component="cart-stock-validator",
    layer="api",
    tags=("cart", "validation"),
)
def test_cart_rejects_zero_quantity(shop, run_context):
    with allure.step("Передать нулевое количество"):
        with pytest.raises(ValueError, match="количество должно быть не меньше 1"):
            shop.cart_summary([("ACC-CASE-XM5", 0)])


@pytest.mark.api
@pytest.mark.regression
@allure_case(
    "AUTO-SHOP-036",
    "Корзина отклоняет отрицательное количество",
    "Проверяет защиту от некорректного изменения количества через API.",
    feature="Корзина",
    story="Управление товарами",
    severity=allure.severity_level.CRITICAL,
    owner="Команда заказа",
    component="cart-stock-validator",
    layer="api",
    tags=("cart", "validation"),
)
def test_cart_rejects_negative_quantity(shop, run_context):
    with allure.step("Передать отрицательное количество"):
        with pytest.raises(ValueError, match="CART-VALIDATION"):
            shop.cart_summary([("ACC-CASE-XM5", -1)])


@pytest.mark.api
@pytest.mark.regression
@allure_case(
    "AUTO-SHOP-037",
    "Корзина отклоняет неизвестный SKU",
    "Проверяет отказ от добавления товара, отсутствующего в каталоге.",
    feature="Корзина",
    story="Управление товарами",
    severity=allure.severity_level.CRITICAL,
    owner="Команда заказа",
    component="cart-service",
    layer="api",
    tags=("cart", "catalog-validation"),
)
def test_cart_rejects_unknown_sku(shop, run_context):
    with allure.step("Добавить отсутствующий товар"):
        with pytest.raises(ValueError, match="CATALOG-404"):
            shop.cart_summary([("UNKNOWN-SKU", 1)])


@pytest.mark.api
@pytest.mark.regression
@allure_case(
    "AUTO-SHOP-038",
    "Все суммы корзины возвращаются в рублях",
    "Проверяет валюту расчёта для отображения и передачи в checkout.",
    feature="Корзина",
    story="Цена и промокоды",
    severity=allure.severity_level.BLOCKER,
    owner="Команда заказа",
    component="cart-pricing-service",
    layer="api",
    tags=("cart", "currency"),
)
def test_cart_currency_is_rub(shop, run_context):
    with allure.step("Рассчитать корзину"):
        cart = shop.cart_summary([("HDP-SONY-XM5", 1)])

    with allure.step("Проверить валюту"):
        assert cart["currency"] == "RUB"


@pytest.mark.api
@pytest.mark.regression
@allure_case(
    "AUTO-SHOP-039",
    "Промокод не применяется ниже минимальной суммы",
    "Проверяет ограничение WELCOME10 для корзин дешевле трёх тысяч рублей.",
    feature="Корзина",
    story="Цена и промокоды",
    severity=allure.severity_level.NORMAL,
    owner="Команда заказа",
    component="promotion-service",
    layer="api",
    tags=("promo", "eligibility"),
)
def test_promocode_is_not_applied_below_minimum(shop, run_context):
    with allure.step("Применить промокод к небольшой корзине"):
        result = shop.apply_promocode(Decimal("1990.00"), "WELCOME10")
        attach_json("Результат промокода", result)

    with allure.step("Проверить отсутствие скидки"):
        assert result["discount"] == "0.00"
        assert result["total"] == "1990.00"


@pytest.mark.api
@pytest.mark.regression
@allure_case(
    "AUTO-SHOP-040",
    "Неизвестный промокод не изменяет цену",
    "Проверяет безопасное поведение для несуществующего или истёкшего кода.",
    feature="Корзина",
    story="Цена и промокоды",
    severity=allure.severity_level.NORMAL,
    owner="Команда заказа",
    component="promotion-service",
    layer="api",
    tags=("promo", "validation"),
)
def test_unknown_promocode_does_not_change_total(shop, run_context):
    with allure.step("Применить неизвестный код"):
        result = shop.apply_promocode(Decimal("25000.00"), "EXPIRED25")

    with allure.step("Проверить исходную сумму"):
        assert result["discount"] == "0.00"
        assert result["total"] == "25000.00"


@pytest.mark.api
@pytest.mark.regression
@allure_case(
    "AUTO-SHOP-041",
    "Скидка по промокоду ограничена тремя тысячами рублей",
    "Проверяет верхнюю границу скидки для дорогой корзины.",
    feature="Корзина",
    story="Цена и промокоды",
    severity=allure.severity_level.CRITICAL,
    owner="Команда заказа",
    component="promotion-service",
    layer="api",
    tags=("promo", "discount-cap"),
)
def test_promocode_discount_has_upper_limit(shop, run_context):
    with allure.step("Применить код к корзине на 80000 рублей"):
        result = shop.apply_promocode(Decimal("80000.00"), "WELCOME10")

    with allure.step("Проверить лимит скидки"):
        assert result["discount"] == "3000.00"
        assert result["total"] == "77000.00"


@pytest.mark.api
@pytest.mark.regression
@allure_case(
    "AUTO-SHOP-042",
    "Промокод уменьшает итог ровно на рассчитанную скидку",
    "Проверяет согласованность полей discount и total в ответе сервиса.",
    feature="Корзина",
    story="Цена и промокоды",
    severity=allure.severity_level.CRITICAL,
    owner="Команда заказа",
    component="promotion-service",
    layer="api",
    tags=("promo", "pricing"),
)
def test_promocode_total_matches_discount(shop, run_context):
    subtotal = Decimal("12000.00")
    with allure.step("Рассчитать скидку"):
        result = shop.apply_promocode(subtotal, "WELCOME10")

    with allure.step("Сверить арифметику"):
        assert Decimal(result["total"]) == subtotal - Decimal(result["discount"])


@pytest.mark.api
@pytest.mark.regression
@allure_case(
    "AUTO-SHOP-043",
    "Однократное применение промокода фиксируется в ответе",
    "Проверяет технический счётчик применения для последующей защиты от повторов.",
    feature="Корзина",
    story="Цена и промокоды",
    severity=allure.severity_level.NORMAL,
    owner="Команда заказа",
    component="promotion-service",
    layer="api",
    tags=("promo", "idempotency"),
)
def test_promocode_response_contains_application_count(shop, run_context):
    with allure.step("Применить промокод один раз"):
        result = shop.apply_promocode(
            Decimal("10000.00"),
            "WELCOME10",
            application_count=1,
        )

    with allure.step("Проверить число применений"):
        assert result["applications"] == 1
