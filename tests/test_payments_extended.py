from decimal import Decimal

import allure
import pytest

from helpers import attach_json, test_case as allure_case


pytestmark = [pytest.mark.testops_demo]


def create_payable_order(shop, customer_id="CUS-DEMO-3001"):
    return shop.create_order(
        customer_id=customer_id,
        lines=[("HDP-SONY-XM5", 1)],
        delivery="pickup",
    )


def payment_callback(order_id, event_id="evt_demo_pay_81001"):
    return {
        "eventId": event_id,
        "idempotencyKey": f"{event_id}:succeeded",
        "paymentId": event_id.replace("evt_", "pay_"),
        "orderId": order_id,
        "status": "succeeded",
        "amount": "34990.00",
        "currency": "RUB",
    }


@pytest.mark.integration
@pytest.mark.smoke
@allure_case(
    "AUTO-SHOP-058",
    "Первичный callback платежа принимается в обработку",
    "Проверяет подтверждение нового события от платёжного провайдера.",
    feature="Оплата и возвраты",
    story="Оплата заказа",
    severity=allure.severity_level.BLOCKER,
    owner="Команда платежей",
    component="payment-callback-handler",
    layer="integration",
    tags=("payment", "callback", "smoke"),
)
def test_payment_callback_is_accepted(shop, run_context):
    order = create_payable_order(shop)
    callback = payment_callback(order["id"])
    with allure.step("Передать callback успешной оплаты"):
        result = shop.process_payment_callback(callback)
        attach_json("Callback", callback)
        attach_json("Результат обработки", result)

    with allure.step("Проверить подтверждение"):
        assert result["httpStatus"] == 200
        assert result["processingResult"] == "accepted"


@pytest.mark.integration
@pytest.mark.regression
@allure_case(
    "AUTO-SHOP-059",
    "Успешный callback переводит заказ в статус Оплачен",
    "Проверяет изменение бизнес-статуса после подтверждения провайдера.",
    feature="Оплата и возвраты",
    story="Оплата заказа",
    severity=allure.severity_level.BLOCKER,
    owner="Команда платежей",
    component="payment-callback-handler",
    layer="integration",
    tags=("payment", "order-status"),
)
def test_successful_callback_marks_order_paid(shop, run_context):
    order = create_payable_order(shop, "CUS-DEMO-3002")
    with allure.step("Обработать успешную оплату"):
        result = shop.process_payment_callback(payment_callback(order["id"]))

    with allure.step("Проверить статус заказа"):
        assert result["orderStatus"] == "Оплачен"
        assert shop.orders[order["id"]]["status"] == "Оплачен"


@pytest.mark.integration
@pytest.mark.regression
@allure_case(
    "AUTO-SHOP-060",
    "Заказ сохраняет идентификатор подтверждённого платежа",
    "Проверяет трассируемость заказа до операции платёжного провайдера.",
    feature="Оплата и возвраты",
    story="Оплата заказа",
    severity=allure.severity_level.CRITICAL,
    owner="Команда платежей",
    component="payment-callback-handler",
    layer="integration",
    tags=("payment", "traceability"),
)
def test_order_stores_payment_id(shop, run_context):
    order = create_payable_order(shop, "CUS-DEMO-3003")
    callback = payment_callback(order["id"], "evt_demo_pay_81003")
    with allure.step("Обработать callback"):
        shop.process_payment_callback(callback)

    with allure.step("Проверить связь заказа с платежом"):
        assert shop.orders[order["id"]]["paymentId"] == callback["paymentId"]


@pytest.mark.integration
@pytest.mark.known_defect
@allure_case(
    "AUTO-SHOP-061",
    "Повторное событие одного платежа не создаёт новую запись",
    "Проверяет дедупликацию по paymentId. Дефект SHOP-915 учитывает только eventId.",
    feature="Оплата и возвраты",
    story="Оплата заказа",
    severity=allure.severity_level.BLOCKER,
    owner="Команда платежей",
    component="payment-callback-handler",
    layer="integration",
    tags=("known-defect", "payment", "idempotency"),
)
def test_same_payment_with_new_event_id_is_deduplicated(shop, run_context):
    order = create_payable_order(shop, "CUS-DEMO-3004")
    first = payment_callback(order["id"], "evt_demo_pay_81004")
    retry = payment_callback(order["id"], "evt_demo_pay_retry_81004")
    retry["paymentId"] = first["paymentId"]
    with allure.step("Обработать исходное событие и повтор с новым eventId"):
        shop.process_payment_callback(first)
        shop.process_payment_callback(retry)
        attach_json("Повторное событие", retry)

    with allure.step("Проверить единственную запись платежа"):
        assert len(shop.payment_events) == 1, (
            "PAYMENT-DUPLICATE: один paymentId зарегистрирован под двумя "
            "eventId [SHOP-915]"
        )


@pytest.mark.api
@pytest.mark.regression
@allure_case(
    "AUTO-SHOP-062",
    "Платёжный сервис отклоняет токен неизвестного формата",
    "Проверяет раннюю валидацию обезличенного платёжного токена.",
    feature="Оплата и возвраты",
    story="Оплата заказа",
    severity=allure.severity_level.BLOCKER,
    owner="Команда платежей",
    component="payment-gateway-adapter",
    layer="api",
    tags=("payment", "validation"),
)
def test_payment_rejects_invalid_token_format(shop, run_context):
    order = create_payable_order(shop, "CUS-DEMO-3006")
    with allure.step("Передать токен неверного формата"):
        with pytest.raises(ValueError, match="PAYMENT-TOKEN-INVALID"):
            shop.pay_by_card(order_id=order["id"], payment_token="card-number-4111")


@pytest.mark.api
@pytest.mark.regression
@allure_case(
    "AUTO-SHOP-063",
    "Оплата не создаётся для неизвестного заказа",
    "Проверяет ссылочную целостность между платёжной операцией и заказом.",
    feature="Оплата и возвраты",
    story="Оплата заказа",
    severity=allure.severity_level.BLOCKER,
    owner="Команда платежей",
    component="payment-gateway-adapter",
    layer="api",
    tags=("payment", "order-validation"),
)
def test_payment_rejects_unknown_order(shop, run_context):
    with allure.step("Оплатить отсутствующий заказ"):
        with pytest.raises(ValueError, match="ORDER-404"):
            shop.pay_by_card(
                order_id="ORD-999999",
                payment_token="tok_demo_visa_1001",
            )


@pytest.mark.api
@pytest.mark.regression
@allure_case(
    "AUTO-SHOP-064",
    "Неоказанная доставка включается в сумму возврата",
    "Проверяет полный возврат стоимости доставки при отмене до передачи заказа.",
    feature="Оплата и возвраты",
    story="Возврат денежных средств",
    severity=allure.severity_level.CRITICAL,
    owner="Команда платежей",
    component="refund-calculation-service",
    layer="api",
    tags=("refund", "delivery"),
)
def test_refund_includes_delivery_before_fulfilment(shop, run_context):
    with allure.step("Рассчитать возврат до доставки"):
        refund = shop.calculate_refund(
            paid_for_item=Decimal("24990.00"),
            delivery_paid=Decimal("390.00"),
            delivery_was_completed=False,
        )
        attach_json("Расчёт возврата", refund)

    with allure.step("Проверить возвращаемую доставку"):
        assert refund["deliveryRefund"] == "390.00"
        assert refund["totalRefund"] == "25380.00"


@pytest.mark.api
@pytest.mark.regression
@allure_case(
    "AUTO-SHOP-065",
    "Бесплатная доставка не увеличивает возврат",
    "Проверяет нулевую компоненту доставки для крупного заказа.",
    feature="Оплата и возвраты",
    story="Возврат денежных средств",
    severity=allure.severity_level.CRITICAL,
    owner="Команда платежей",
    component="refund-calculation-service",
    layer="api",
    tags=("refund", "delivery"),
)
def test_free_delivery_adds_nothing_to_refund(shop, run_context):
    with allure.step("Рассчитать возврат с бесплатной доставкой"):
        refund = shop.calculate_refund(
            paid_for_item=Decimal("129990.00"),
            delivery_paid=Decimal("0.00"),
            delivery_was_completed=False,
        )

    with allure.step("Проверить итог"):
        assert refund["deliveryRefund"] == "0.00"
        assert refund["totalRefund"] == "129990.00"


@pytest.mark.api
@pytest.mark.regression
@allure_case(
    "AUTO-SHOP-066",
    "Сумма возврата округляется до копеек",
    "Проверяет денежное округление после пропорционального распределения скидки.",
    feature="Оплата и возвраты",
    story="Возврат денежных средств",
    severity=allure.severity_level.CRITICAL,
    owner="Команда платежей",
    component="refund-calculation-service",
    layer="api",
    tags=("refund", "rounding"),
)
def test_refund_is_rounded_to_kopecks(shop, run_context):
    with allure.step("Передать сумму после распределения скидки"):
        refund = shop.calculate_refund(
            paid_for_item=Decimal("1234.567"),
            delivery_paid=Decimal("0"),
            delivery_was_completed=False,
        )

    with allure.step("Проверить округление"):
        assert refund["itemRefund"] == "1234.57"
        assert refund["totalRefund"] == "1234.57"


@pytest.mark.api
@pytest.mark.regression
@allure_case(
    "AUTO-SHOP-067",
    "Возврат только доставки поддерживается сервисом",
    "Проверяет отмену заказа без оплаченных товарных позиций.",
    feature="Оплата и возвраты",
    story="Возврат денежных средств",
    severity=allure.severity_level.NORMAL,
    owner="Команда платежей",
    component="refund-calculation-service",
    layer="api",
    tags=("refund", "delivery"),
)
def test_delivery_only_refund_is_supported(shop, run_context):
    with allure.step("Рассчитать возврат только доставки"):
        refund = shop.calculate_refund(
            paid_for_item=Decimal("0"),
            delivery_paid=Decimal("390"),
            delivery_was_completed=False,
        )

    with allure.step("Проверить компоненты"):
        assert refund["itemRefund"] == "0.00"
        assert refund["totalRefund"] == "390.00"


@pytest.mark.api
@pytest.mark.regression
@allure_case(
    "AUTO-SHOP-068",
    "Итог возврата равен сумме его компонентов",
    "Проверяет согласованность товарной и логистической частей расчёта.",
    feature="Оплата и возвраты",
    story="Возврат денежных средств",
    severity=allure.severity_level.BLOCKER,
    owner="Команда платежей",
    component="refund-calculation-service",
    layer="api",
    tags=("refund", "calculation"),
)
def test_refund_total_matches_components(shop, run_context):
    with allure.step("Рассчитать частичный возврат"):
        refund = shop.calculate_refund(
            paid_for_item=Decimal("41990.00"),
            delivery_paid=Decimal("490.00"),
            delivery_was_completed=False,
        )

    with allure.step("Сверить сумму компонентов"):
        expected = Decimal(refund["itemRefund"]) + Decimal(refund["deliveryRefund"])
        assert Decimal(refund["totalRefund"]) == expected


@pytest.mark.integration
@pytest.mark.known_defect
@allure_case(
    "AUTO-SHOP-069",
    "Callback неизвестного заказа помещается в карантин",
    "Проверяет обработку запоздавшего события. Дефект SHOP-811 приводит к Broken из-за KeyError.",
    feature="Оплата и возвраты",
    story="Оплата заказа",
    severity=allure.severity_level.CRITICAL,
    owner="Команда платежей",
    component="payment-callback-handler",
    layer="integration",
    tags=("broken", "payment", "orphan-event"),
)
def test_orphan_payment_callback_is_quarantined(shop, run_context):
    callback = payment_callback("ORD-REMOVED-81009", "evt_demo_pay_81009")
    with allure.step("Получить callback удалённого заказа"):
        attach_json("Запоздавший callback", callback)
        result = shop.process_payment_callback(callback)

    with allure.step("Проверить помещение события в карантин"):
        assert result["processingResult"] == "quarantined"


@pytest.mark.integration
@pytest.mark.flaky
@allure_case(
    "AUTO-SHOP-070",
    "Подтверждённый платёж появляется в операционном журнале",
    "Проверяет асинхронную проекцию платежа. Индексатор отстаёт с вероятностью 40%.",
    feature="Оплата и возвраты",
    story="Оплата заказа",
    severity=allure.severity_level.CRITICAL,
    owner="Команда платежей",
    component="payment-ledger-indexer",
    layer="integration",
    tags=("flaky", "payment", "eventual-consistency"),
)
def test_payment_appears_in_operational_ledger(
    shop,
    run_context,
    flaky_demo_check,
):
    order = create_payable_order(shop, "CUS-DEMO-3010")
    callback = payment_callback(order["id"], "evt_demo_pay_81010")
    with allure.step("Обработать подтверждение платежа"):
        shop.process_payment_callback(callback)

    with allure.step("Дождаться обновления операционного журнала"):
        flaky_demo_check(
            "PAYMENT-LEDGER-TIMEOUT: платёж принят, но запись не появилась "
            "в read-model за 5 секунд; lag очереди payments-ledger 96 [SHOP-826]",
            subsystem="payment-ledger-indexer",
        )

    with allure.step("Проверить исходное событие"):
        assert callback["eventId"] in shop.payment_events
