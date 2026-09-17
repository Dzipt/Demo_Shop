from decimal import Decimal

import allure
import pytest

from helpers import attach_json


pytestmark = [pytest.mark.testops_demo]


@pytest.mark.integration
@pytest.mark.smoke
@pytest.mark.slow_demo
@allure.label("external_id", "AUTO-SHOP-013")
@allure.title("Повторный callback не создаёт второй платёж")
@allure.description(
    "Проверяет идемпотентную обработку двух одинаковых callback платёжного провайдера. "
    "Заказ должен перейти в статус «Оплачен» один раз."
)
@allure.epic("Интернет-магазин")
@allure.feature("Оплата и возвраты")
@allure.story("Оплата заказа")
@allure.severity(allure.severity_level.BLOCKER)
@allure.label("owner", "Команда платежей")
@allure.label("component", "payment-callback-handler")
@allure.label("layer", "integration")
@allure.tag("smoke", "payment", "idempotency")
def test_duplicate_payment_callback_is_idempotent(shop, run_context, demo_delay):
    with allure.step("Создать заказ, ожидающий оплату"):
        order = shop.create_order(
            customer_id="CUS-DEMO-1042",
            lines=[("HDP-SONY-XM5", 1)],
            delivery="pickup",
        )

    callback = {
        "eventId": "evt_demo_pay_75018_01",
        "idempotencyKey": "pay_demo_75018:succeeded",
        "paymentId": "pay_demo_75018",
        "orderId": order["id"],
        "status": "succeeded",
        "amount": "34990.00",
        "currency": "RUB",
    }
    with allure.step("Обработать исходный callback"):
        first = shop.process_payment_callback(callback)
        attach_json("Исходный callback", callback)
        attach_json("Первый результат обработки", first)

    with allure.step("Повторно доставить то же событие"):
        demo_delay("Имитация повторной доставки callback для live-обновления запуска")
        second = shop.process_payment_callback(callback)
        attach_json("Результат повторной обработки", second)

    with allure.step("Проверить итоговое состояние заказа и платежа"):
        assert first["processingResult"] == "accepted"
        assert second["processingResult"] == "duplicate_ignored"
        assert second["paymentRecords"] == 1
        assert second["orderStatus"] == "Оплачен"
        assert len(shop.payment_events) == 1


@pytest.mark.integration
@pytest.mark.known_defect
@allure.label("external_id", "AUTO-SHOP-014")
@allure.title("Оплата заказа картой проходит через платёжный шлюз")
@allure.description(
    "Проверяет техническую доступность защищённого канала к sandbox-провайдеру. "
    "Истёкший TLS-сертификат приводит к Broken, поскольку сценарий не дошёл до "
    "проверки бизнес-результата."
)
@allure.epic("Интернет-магазин")
@allure.feature("Оплата и возвраты")
@allure.story("Оплата заказа")
@allure.severity(allure.severity_level.BLOCKER)
@allure.label("owner", "Команда платежей")
@allure.label("component", "payment-gateway-adapter")
@allure.label("layer", "integration")
@allure.tag("broken", "payment", "tls", "infrastructure")
def test_card_payment_is_sent_to_gateway(shop, run_context):
    with allure.step("Создать заказ, готовый к оплате"):
        order = shop.create_order(
            customer_id="CUS-DEMO-3091",
            lines=[("HDP-SONY-XM5", 1)],
            delivery="pickup",
        )
        assert order["status"] == "Создан"

    with allure.step("Подготовить обезличенный запрос"):
        request = {
            "orderId": order["id"],
            "amount": "34990.00",
            "currency": "RUB",
            "paymentToken": "tok_demo_********9142",
        }
        attach_json("Запрос на оплату", request)

    with allure.step("Отправить запрос по защищённому соединению"):
        shop.pay_by_card(
            order_id=order["id"],
            payment_token="tok_demo_visa_9142",
        )


@pytest.mark.api
@pytest.mark.known_defect
@allure.label("external_id", "AUTO-SHOP-015")
@allure.title("Сумма возврата учитывает скидку и не возвращает оказанную доставку")
@allure.description(
    "Проверяет частичный возврат товара после применения скидки. Известный дефект "
    "SHOP-619 ошибочно добавляет стоимость уже оказанной доставки к возврату."
)
@allure.epic("Интернет-магазин")
@allure.feature("Оплата и возвраты")
@allure.story("Возврат денежных средств")
@allure.severity(allure.severity_level.BLOCKER)
@allure.label("owner", "Команда платежей")
@allure.label("component", "refund-calculation-service")
@allure.label("layer", "api")
@allure.tag("known-defect", "refund", "pricing")
def test_refund_excludes_completed_delivery(shop, run_context):
    with allure.step("Подготовить оплаченные суммы заказа"):
        calculation = {
            "itemListPrice": "34990.00",
            "allocatedDiscount": "3000.00",
            "paidForItem": "31990.00",
            "deliveryPaid": "390.00",
            "deliveryWasCompleted": True,
        }
        attach_json("Исходные данные возврата", calculation)

    with allure.step("Рассчитать возврат"):
        refund = shop.calculate_refund(
            paid_for_item=Decimal(calculation["paidForItem"]),
            delivery_paid=Decimal(calculation["deliveryPaid"]),
            delivery_was_completed=True,
        )
        attach_json("Расчёт сервиса возвратов", refund)

    with allure.step("Проверить сумму без стоимости оказанной доставки"):
        assert refund["deliveryRefund"] == "0.00", (
            "REFUND-DELIVERY-ALREADY-COMPLETED: сервис вернул стоимость оказанной "
            f"доставки {refund['deliveryRefund']} руб. [SHOP-619]"
        )
        assert refund["totalRefund"] == "31990.00"
