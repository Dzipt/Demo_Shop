import allure
import pytest

from helpers import attach_json


pytestmark = [pytest.mark.testops_demo]


@pytest.mark.e2e
@pytest.mark.smoke
@allure.label("external_id", "AUTO-SHOP-009")
@allure.title("Заказ создаётся из актуальной корзины покупателя")
@allure.description(
    "Проверяет создание заказа с корректным покупателем, составом, способом доставки "
    "и суммой. Риск: заказ невозможно сопоставить с расчётом корзины."
)
@allure.epic("Интернет-магазин")
@allure.feature("Оформление заказа")
@allure.story("Данные покупателя")
@allure.severity(allure.severity_level.BLOCKER)
@allure.label("owner", "Команда заказа")
@allure.label("component", "checkout-service")
@allure.label("layer", "e2e")
@allure.tag("smoke", "checkout")
def test_order_is_created_from_customer_cart(shop, run_context):
    with allure.step("Создать заказ авторизованного покупателя"):
        order = shop.create_order(
            customer_id="CUS-DEMO-1042",
            lines=[("HDP-SONY-XM5", 1)],
            delivery="courier",
        )
        attach_json("Созданный заказ", order)

    with allure.step("Проверить основные атрибуты заказа"):
        assert order["id"].startswith("ORD-")
        assert order["customerId"] == "CUS-DEMO-1042"
        assert order["status"] == "Создан"
        assert order["deliveryMethod"] == "courier"
        assert order["total"] == "35380.00"
        assert [item["sku"] for item in order["items"]] == ["HDP-SONY-XM5"]


@pytest.mark.integration
@pytest.mark.regression
@allure.label("external_id", "AUTO-SHOP-010")
@allure.title("Согласие на обработку данных фиксируется в заказе")
@allure.description(
    "Проверяет связь заказа с принятой версией согласия и создание единственного "
    "аудит-события без платёжных реквизитов."
)
@allure.epic("Интернет-магазин")
@allure.feature("Оформление заказа")
@allure.story("Данные покупателя")
@allure.severity(allure.severity_level.CRITICAL)
@allure.label("owner", "Команда заказа")
@allure.label("component", "consent-audit-service")
@allure.label("layer", "integration")
@allure.tag("regression", "consent", "audit")
def test_consent_is_recorded_for_order(shop, run_context):
    with allure.step("Создать заказ"):
        order = shop.create_order(
            customer_id="CUS-DEMO-1042",
            lines=[("HDP-APPLE-PRO2", 1)],
            delivery="courier",
        )

    with allure.step("Зафиксировать принятие версии privacy-2026-08"):
        event = shop.record_consent(
            order_id=order["id"],
            customer_id="CUS-DEMO-1042",
            policy_version="privacy-2026-08",
            accepted_at="2026-08-14T12:41:35Z",
        )
        attach_json("Событие согласия", event)

    with allure.step("Проверить заказ и аудит-событие"):
        stored = shop.orders[order["id"]]
        assert stored["consentAccepted"] is True
        assert stored["consentPolicyVersion"] == "privacy-2026-08"
        assert event["accepted"] is True
        assert event["orderId"] == order["id"]
        assert len(shop.consent_events) == 1
        assert "payment" not in event


@pytest.mark.api
@pytest.mark.regression
@pytest.mark.slow_demo
@pytest.mark.parametrize(
    (
        "city",
        "address",
        "expected_zone",
        "expected_available",
        "expected_price",
        "expected_sla",
    ),
    [
        pytest.param("Москва", "ул. Тверская д. 12", "A", True, 290, 1, id="moscow-a"),
        pytest.param("Москва", "ул. Новомосковская д. 17", "B", True, 390, 1, id="moscow-b"),
        pytest.param("Химки", "Ленинградское ш. д. 8", "C", True, 590, 2, id="khimki-c"),
        pytest.param("Казань", "ул. Баумана д. 44", "A", True, 390, 2, id="kazan"),
        pytest.param("Новосибирск", "Красный проспект д. 81", "B", True, 490, 3, id="novosibirsk"),
        pytest.param(
            "Норильск",
            "Ленинский проспект д. 21",
            "Удалённая",
            False,
            None,
            None,
            id="norilsk",
        ),
    ],
)
@allure.label("external_id", "AUTO-SHOP-011")
@allure.title("Доступность курьерской доставки: {city}, {address}")
@allure.description(
    "Проверяет зону, тариф, SLA и альтернативу доставки для адресов из разных регионов. "
    "Шесть наборов остаются одним логическим тест-кейсом в TestOps."
)
@allure.epic("Интернет-магазин")
@allure.feature("Оформление заказа")
@allure.story("Доставка и подтверждение")
@allure.severity(allure.severity_level.CRITICAL)
@allure.label("owner", "Команда заказа")
@allure.label("component", "delivery-routing-service")
@allure.label("layer", "api")
@allure.tag("regression", "delivery", "parameterized")
def test_courier_delivery_is_calculated_for_address(
    shop,
    run_context,
    demo_delay,
    city,
    address,
    expected_zone,
    expected_available,
    expected_price,
    expected_sla,
):
    with allure.step("Передать адрес в сервис маршрутизации"):
        quote = shop.delivery_quote(city, address)
        attach_json("Расчёт доставки", quote)

    with allure.step("Дождаться ответа тарифного сервиса"):
        demo_delay("Имитация расчёта маршрута для live-обновления запуска")

    with allure.step("Сверить зону, доступность, цену и срок"):
        assert quote["zone"] == expected_zone
        assert quote["courierAvailable"] is expected_available
        assert quote["price"] == expected_price
        assert quote["slaDays"] == expected_sla
        if not expected_available:
            assert quote["alternative"] == "Доставка в пункт выдачи"


@pytest.mark.e2e
@pytest.mark.flaky
@allure.label("external_id", "AUTO-SHOP-012")
@allure.title("Созданный заказ появляется в истории покупателя")
@allure.description(
    "Проверяет асинхронную проекцию истории заказов. Проверка падает с вероятностью "
    "40%, воспроизводя отставание индексатора после создания заказа."
)
@allure.epic("Интернет-магазин")
@allure.feature("Оформление заказа")
@allure.story("Доставка и подтверждение")
@allure.severity(allure.severity_level.CRITICAL)
@allure.label("owner", "Команда заказа")
@allure.label("component", "order-history-indexer")
@allure.label("layer", "e2e")
@allure.tag("flaky", "eventual-consistency", "order-history")
def test_created_order_appears_in_customer_history(
    shop,
    run_context,
    flaky_demo_check,
):
    with allure.step("Создать заказ покупателя"):
        order = shop.create_order(
            customer_id="CUS-DEMO-2048",
            lines=[("PHN-SAMSUNG-S24", 1)],
            delivery="courier",
        )
        attach_json("Событие создания заказа", order)

    with allure.step("Дождаться обновления read-model истории"):
        flaky_demo_check(
            f"ORDER-HISTORY-TIMEOUT: заказ {order['id']} создан, но событие "
            f"{order['historyIndexEvent']} не обработано за 5 секунд; lag очереди "
            "order-history достиг 184 сообщений [SHOP-421]",
            subsystem="order-history-indexer",
        )

    with allure.step("Сверить проекцию с источником"):
        stored = shop.orders[order["id"]]
        assert stored["customerId"] == "CUS-DEMO-2048"
        assert stored["total"] == order["total"]
