from decimal import Decimal

import allure
import pytest

from helpers import attach_csv, attach_json


pytestmark = [pytest.mark.testops_demo]


@pytest.mark.api
@pytest.mark.smoke
@pytest.mark.parametrize(
    ("lines", "expected_subtotal", "expected_delivery", "expected_total"),
    [
        pytest.param([("HDP-APPLE-PRO2", 1)], "24990.00", "390.00", "25380.00", id="one-item"),
        pytest.param([("HDP-SONY-XM5", 2)], "69980.00", "390.00", "70370.00", id="two-items"),
        pytest.param(
            [("PHN-APPLE-15", 1), ("HDP-APPLE-PRO2", 1)],
            "104980.00",
            "0.00",
            "104980.00",
            id="free-delivery",
        ),
        pytest.param(
            [("LAP-LENOVO-T14", 1), ("HDP-SONY-XM5", 1)],
            "184980.00",
            "0.00",
            "184980.00",
            id="two-expensive-lines",
        ),
    ],
)
@allure.label("external_id", "AUTO-SHOP-005")
@allure.title("Корзина рассчитывает итог для набора {lines}")
@allure.description(
    "Проверяет суммы строк, подытог, доставку и итог для разных составов корзины. "
    "Бесплатная доставка включается при сумме товаров от 100 000 рублей."
)
@allure.epic("Интернет-магазин")
@allure.feature("Корзина")
@allure.story("Управление товарами")
@allure.severity(allure.severity_level.BLOCKER)
@allure.label("owner", "Команда заказа")
@allure.label("component", "cart-pricing-service")
@allure.label("layer", "api")
@allure.tag("smoke", "pricing", "parameterized")
def test_cart_total_is_calculated_correctly(
    shop,
    run_context,
    lines,
    expected_subtotal,
    expected_delivery,
    expected_total,
):
    with allure.step("Сформировать корзину"):
        attach_json("Состав корзины", {"lines": lines})

    with allure.step("Получить расчёт стоимости"):
        summary = shop.cart_summary(lines)
        attach_json("Расчёт корзины", summary)
        attach_csv(
            "Строки корзины",
            [["SKU", "Количество", "Цена", "Сумма"]]
            + [
                [line["sku"], line["quantity"], line["unitPrice"], line["lineTotal"]]
                for line in summary["lines"]
            ],
        )

    with allure.step("Сверить денежные значения"):
        assert summary["subtotal"] == expected_subtotal
        assert summary["delivery"] == expected_delivery
        assert summary["total"] == expected_total
        assert summary["currency"] == "RUB"


@pytest.mark.api
@pytest.mark.regression
@allure.label("external_id", "AUTO-SHOP-006")
@allure.title("Корзина отклоняет количество больше доступного остатка")
@allure.description(
    "Проверяет защиту от оформления товара сверх складского остатка. "
    "Ответ должен содержать SKU, запрошенное и доступное количество."
)
@allure.epic("Интернет-магазин")
@allure.feature("Корзина")
@allure.story("Управление товарами")
@allure.severity(allure.severity_level.CRITICAL)
@allure.label("owner", "Команда заказа")
@allure.label("component", "cart-stock-validator")
@allure.label("layer", "api")
@allure.tag("regression", "validation", "stock")
def test_cart_rejects_quantity_above_stock(shop, run_context):
    with allure.step("Запросить 6 ноутбуков при остатке 5"):
        with pytest.raises(ValueError) as error:
            shop.cart_summary([("LAP-APPLE-AIR13", 6)])

    with allure.step("Проверить диагностическое сообщение"):
        message = str(error.value)
        allure.attach(message, "Ответ валидатора", allure.attachment_type.TEXT)
        assert "CART-STOCK-CONFLICT" in message
        assert "запрошено 6" in message
        assert "доступно 5" in message


@pytest.mark.api
@pytest.mark.smoke
@allure.label("external_id", "AUTO-SHOP-007")
@allure.title("Промокод WELCOME10 применяет скидку с верхним лимитом")
@allure.description(
    "Проверяет действующий промокод: скидка равна 10%, но не превышает 3 000 рублей."
)
@allure.epic("Интернет-магазин")
@allure.feature("Корзина")
@allure.story("Цена и промокоды")
@allure.severity(allure.severity_level.CRITICAL)
@allure.label("owner", "Команда заказа")
@allure.label("component", "promotion-service")
@allure.label("layer", "api")
@allure.tag("smoke", "promo", "pricing")
def test_promocode_applies_expected_discount(shop, run_context):
    with allure.step("Применить WELCOME10 к корзине на 45 000 рублей"):
        result = shop.apply_promocode(Decimal("45000.00"), "WELCOME10")
        attach_json("Ответ сервиса промокодов", result)

    with allure.step("Проверить лимит скидки и итог"):
        assert result["discount"] == "3000.00"
        assert result["total"] == "42000.00"
        assert result["applications"] == 1


@pytest.mark.api
@pytest.mark.known_defect
@allure.label("external_id", "AUTO-SHOP-008")
@allure.title("Повторное применение промокода не увеличивает скидку")
@allure.description(
    "Проверяет идемпотентность WELCOME10 при повторной отправке запроса. "
    "Известный дефект SHOP-487 приводит к повторному вычитанию скидки."
)
@allure.epic("Интернет-магазин")
@allure.feature("Корзина")
@allure.story("Цена и промокоды")
@allure.severity(allure.severity_level.BLOCKER)
@allure.label("owner", "Команда заказа")
@allure.label("component", "promotion-service")
@allure.label("layer", "api")
@allure.tag("known-defect", "pricing", "idempotency")
def test_promocode_is_idempotent_on_retry(shop, run_context):
    subtotal = Decimal("79990.00")
    with allure.step("Применить промокод первый раз"):
        first = shop.apply_promocode(subtotal, "WELCOME10", application_count=1)
        attach_json("Первое применение", first)
        assert first["total"] == "76990.00"

    with allure.step("Повторить тот же запрос после сетевого таймаута"):
        retry = shop.apply_promocode(subtotal, "WELCOME10", application_count=2)
        attach_json("Повторный ответ", retry)

    with allure.step("Убедиться, что повтор не изменил сумму"):
        assert retry["total"] == first["total"], (
            "PROMO-IDEMPOTENCY-VIOLATION: повторный запрос WELCOME10 изменил итог "
            f"с {first['total']} до {retry['total']}; скидка выросла "
            f"с {first['discount']} до {retry['discount']} [SHOP-487]"
        )
