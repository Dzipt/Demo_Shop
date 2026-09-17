import allure
import pytest

from helpers import attach_json, test_case as allure_case


pytestmark = [pytest.mark.testops_demo]


@pytest.mark.e2e
@pytest.mark.smoke
@allure_case(
    "AUTO-SHOP-044",
    "Каждый заказ получает уникальный номер",
    "Проверяет отсутствие коллизий при последовательном оформлении заказов.",
    feature="Оформление заказа",
    story="Данные покупателя",
    severity=allure.severity_level.BLOCKER,
    owner="Команда заказа",
    component="checkout-service",
    layer="e2e",
    tags=("checkout", "order-id", "smoke"),
)
def test_each_order_has_unique_id(shop, run_context):
    with allure.step("Оформить два заказа"):
        first = shop.create_order(
            customer_id="CUS-DEMO-1001",
            lines=[("ACC-CASE-XM5", 1)],
            delivery="pickup",
        )
        second = shop.create_order(
            customer_id="CUS-DEMO-1002",
            lines=[("HDP-APPLE-PRO2", 1)],
            delivery="courier",
        )

    with allure.step("Сравнить номера"):
        assert first["id"] != second["id"]
        assert first["id"].startswith("ORD-")
        assert second["id"].startswith("ORD-")


@pytest.mark.api
@pytest.mark.regression
@allure_case(
    "AUTO-SHOP-045",
    "Новый заказ создаётся в начальном статусе",
    "Проверяет, что неоплаченный заказ не получает преждевременно следующий статус.",
    feature="Оформление заказа",
    story="Данные покупателя",
    severity=allure.severity_level.BLOCKER,
    owner="Команда заказа",
    component="checkout-service",
    layer="api",
    tags=("checkout", "status"),
)
def test_new_order_has_created_status(shop, run_context):
    with allure.step("Создать заказ"):
        order = shop.create_order(
            customer_id="CUS-DEMO-1101",
            lines=[("PHN-APPLE-15", 1)],
            delivery="courier",
        )

    with allure.step("Проверить начальный статус"):
        assert order["status"] == "Создан"


@pytest.mark.api
@pytest.mark.regression
@allure_case(
    "AUTO-SHOP-046",
    "Заказ сохраняет идентификатор покупателя",
    "Проверяет связь заказа с обезличенной учетной записью клиента.",
    feature="Оформление заказа",
    story="Данные покупателя",
    severity=allure.severity_level.CRITICAL,
    owner="Команда заказа",
    component="checkout-service",
    layer="api",
    tags=("checkout", "customer"),
)
def test_order_preserves_customer_id(shop, run_context):
    with allure.step("Оформить заказ покупателя"):
        order = shop.create_order(
            customer_id="CUS-DEMO-1201",
            lines=[("HDP-SONY-XM5", 1)],
            delivery="pickup",
        )

    with allure.step("Проверить владельца заказа"):
        assert order["customerId"] == "CUS-DEMO-1201"


@pytest.mark.api
@pytest.mark.regression
@allure_case(
    "AUTO-SHOP-047",
    "Заказ сохраняет выбранный способ доставки",
    "Проверяет передачу способа получения из checkout в заказ.",
    feature="Оформление заказа",
    story="Доставка и подтверждение",
    severity=allure.severity_level.CRITICAL,
    owner="Команда заказа",
    component="checkout-service",
    layer="api",
    tags=("checkout", "delivery"),
)
def test_order_preserves_delivery_method(shop, run_context):
    with allure.step("Оформить самовывоз"):
        order = shop.create_order(
            customer_id="CUS-DEMO-1301",
            lines=[("ACC-CASE-XM5", 1)],
            delivery="pickup",
        )

    with allure.step("Проверить способ получения"):
        assert order["deliveryMethod"] == "pickup"


@pytest.mark.api
@pytest.mark.flaky
@allure_case(
    "AUTO-SHOP-048",
    "Позиции корзины переносятся в заказ без потерь",
    "Проверяет асинхронную проекцию состава заказа. Проекция отстаёт с вероятностью 40%.",
    feature="Оформление заказа",
    story="Данные покупателя",
    severity=allure.severity_level.BLOCKER,
    owner="Команда заказа",
    component="checkout-service",
    layer="api",
    tags=("flaky", "checkout", "eventual-consistency"),
)
def test_cart_lines_are_copied_to_order(shop, run_context, flaky_demo_check):
    with allure.step("Оформить заказ с двумя товарами"):
        order = shop.create_order(
            customer_id="CUS-DEMO-1401",
            lines=[("HDP-APPLE-PRO2", 1), ("ACC-CASE-XM5", 2)],
            delivery="courier",
        )
        attach_json("Заказ", order)

    with allure.step("Дождаться проекции состава заказа"):
        flaky_demo_check(
            "ORDER-ITEMS-PROJECTION-LAG: состав заказа не появился в read-model "
            "за 5 секунд [SHOP-873]",
            subsystem="order-items-projector",
        )

    with allure.step("Проверить состав"):
        assert [(item["sku"], item["quantity"]) for item in order["items"]] == [
            ("HDP-APPLE-PRO2", 1),
            ("ACC-CASE-XM5", 2),
        ]


@pytest.mark.api
@pytest.mark.regression
@allure_case(
    "AUTO-SHOP-049",
    "Итог заказа совпадает с итогом корзины",
    "Проверяет отсутствие изменения цены между корзиной и созданием заказа.",
    feature="Оформление заказа",
    story="Данные покупателя",
    severity=allure.severity_level.BLOCKER,
    owner="Команда заказа",
    component="checkout-service",
    layer="integration",
    tags=("checkout", "pricing"),
)
def test_order_total_matches_cart_total(shop, run_context):
    lines = [("PHN-SAMSUNG-S24", 1), ("ACC-CASE-XM5", 1)]
    with allure.step("Рассчитать корзину и создать заказ"):
        cart = shop.cart_summary(lines)
        order = shop.create_order(
            customer_id="CUS-DEMO-1501",
            lines=lines,
            delivery="courier",
        )

    with allure.step("Сверить суммы"):
        assert order["total"] == cart["total"]
        assert order["currency"] == cart["currency"]


@pytest.mark.api
@pytest.mark.regression
@allure_case(
    "AUTO-SHOP-050",
    "Заказ не создаётся для отсутствующего товара",
    "Проверяет атомарный отказ checkout при неизвестном SKU.",
    feature="Оформление заказа",
    story="Данные покупателя",
    severity=allure.severity_level.BLOCKER,
    owner="Команда заказа",
    component="checkout-service",
    layer="integration",
    tags=("checkout", "catalog-validation"),
)
def test_order_is_not_created_for_unknown_sku(shop, run_context):
    with allure.step("Оформить заказ с неизвестным SKU"):
        with pytest.raises(ValueError, match="CATALOG-404"):
            shop.create_order(
                customer_id="CUS-DEMO-1601",
                lines=[("UNKNOWN-SKU", 1)],
                delivery="courier",
            )

    with allure.step("Проверить отсутствие заказа"):
        assert shop.orders == {}


@pytest.mark.api
@pytest.mark.regression
@allure_case(
    "AUTO-SHOP-051",
    "Заказ не создаётся при недостаточном остатке",
    "Проверяет повторную серверную валидацию остатка на этапе checkout.",
    feature="Оформление заказа",
    story="Данные покупателя",
    severity=allure.severity_level.BLOCKER,
    owner="Команда заказа",
    component="checkout-service",
    layer="integration",
    tags=("checkout", "stock"),
)
def test_order_is_not_created_above_stock(shop, run_context):
    with allure.step("Запросить количество выше остатка"):
        with pytest.raises(ValueError, match="CART-STOCK-CONFLICT"):
            shop.create_order(
                customer_id="CUS-DEMO-1701",
                lines=[("LAP-LENOVO-T14", 5)],
                delivery="courier",
            )

    with allure.step("Проверить отсутствие заказа"):
        assert len(shop.orders) == 0


@pytest.mark.integration
@pytest.mark.regression
@allure_case(
    "AUTO-SHOP-052",
    "Согласие нельзя записать для неизвестного заказа",
    "Проверяет ссылочную целостность журнала пользовательских согласий.",
    feature="Оформление заказа",
    story="Данные покупателя",
    severity=allure.severity_level.CRITICAL,
    owner="Команда заказа",
    component="consent-audit-service",
    layer="integration",
    tags=("consent", "validation"),
)
def test_consent_rejects_unknown_order(shop, run_context):
    with allure.step("Записать согласие для отсутствующего заказа"):
        with pytest.raises(ValueError, match="ORDER-404"):
            shop.record_consent(
                order_id="ORD-999999",
                customer_id="CUS-DEMO-1801",
                policy_version="privacy-2026-08",
                accepted_at="2026-08-20T10:15:00Z",
            )


@pytest.mark.integration
@pytest.mark.flaky
@allure_case(
    "AUTO-SHOP-053",
    "Повторная запись согласия не создаёт дубль события",
    "Проверяет идемпотентность и репликацию аудита. Реплика отстаёт с вероятностью 40%.",
    feature="Оформление заказа",
    story="Данные покупателя",
    severity=allure.severity_level.CRITICAL,
    owner="Команда заказа",
    component="consent-audit-service",
    layer="integration",
    tags=("flaky", "consent", "eventual-consistency"),
)
def test_consent_recording_is_idempotent(shop, run_context, flaky_demo_check):
    order = shop.create_order(
        customer_id="CUS-DEMO-1901",
        lines=[("ACC-CASE-XM5", 1)],
        delivery="pickup",
    )
    payload = {
        "order_id": order["id"],
        "customer_id": "CUS-DEMO-1901",
        "policy_version": "privacy-2026-08",
        "accepted_at": "2026-08-20T10:20:00Z",
    }
    with allure.step("Дважды записать одинаковое согласие"):
        first = shop.record_consent(**payload)
        second = shop.record_consent(**payload)

    with allure.step("Дождаться обновления аудиторской реплики"):
        flaky_demo_check(
            "CONSENT-AUDIT-LAG: событие согласия не найдено в аудиторской "
            "реплике за 5 секунд [SHOP-881]",
            subsystem="consent-audit-replica",
        )

    with allure.step("Проверить единственное событие"):
        assert first["eventId"] == second["eventId"]
        assert len(shop.consent_events) == 1


@pytest.mark.integration
@pytest.mark.known_defect
@allure_case(
    "AUTO-SHOP-054",
    "Версия принятой политики не может быть понижена",
    "Проверяет защиту аудита от устаревшего события. Дефект SHOP-889 перезаписывает новую версию старой.",
    feature="Оформление заказа",
    story="Данные покупателя",
    severity=allure.severity_level.CRITICAL,
    owner="Команда заказа",
    component="consent-audit-service",
    layer="integration",
    tags=("known-defect", "consent", "versioning"),
)
def test_order_stores_consent_policy_version(shop, run_context):
    order = shop.create_order(
        customer_id="CUS-DEMO-2001",
        lines=[("HDP-SONY-XM5", 1)],
        delivery="courier",
    )
    with allure.step("Принять актуальную политику"):
        shop.record_consent(
            order_id=order["id"],
            customer_id="CUS-DEMO-2001",
            policy_version="privacy-2026-09",
            accepted_at="2026-09-01T08:00:00Z",
        )

    with allure.step("Получить запоздавшее событие старой версии"):
        shop.record_consent(
            order_id=order["id"],
            customer_id="CUS-DEMO-2001",
            policy_version="privacy-2026-08",
            accepted_at="2026-08-20T08:00:00Z",
        )

    with allure.step("Проверить, что версия не понизилась"):
        assert shop.orders[order["id"]]["consentPolicyVersion"] == "privacy-2026-09"


@pytest.mark.integration
@pytest.mark.regression
@allure_case(
    "AUTO-SHOP-055",
    "Событие согласия содержит канал оформления",
    "Проверяет источник события для последующего аудита пользовательского пути.",
    feature="Оформление заказа",
    story="Данные покупателя",
    severity=allure.severity_level.NORMAL,
    owner="Команда заказа",
    component="consent-audit-service",
    layer="integration",
    tags=("consent", "audit"),
)
def test_consent_event_contains_checkout_channel(shop, run_context):
    order = shop.create_order(
        customer_id="CUS-DEMO-2101",
        lines=[("ACC-CASE-XM5", 1)],
        delivery="pickup",
    )
    with allure.step("Зафиксировать согласие"):
        event = shop.record_consent(
            order_id=order["id"],
            customer_id="CUS-DEMO-2101",
            policy_version="privacy-2026-09",
            accepted_at="2026-09-01T08:05:00Z",
        )
        attach_json("Аудит-событие", event)

    with allure.step("Проверить канал"):
        assert event["channel"] == "web-checkout"


@pytest.mark.api
@pytest.mark.known_defect
@allure_case(
    "AUTO-SHOP-056",
    "Слот курьерской доставки резервируется для подтверждённого адреса",
    "Проверяет связь с сервисом слотов. Недоступность сервиса приводит к Broken.",
    feature="Оформление заказа",
    story="Доставка и подтверждение",
    severity=allure.severity_level.CRITICAL,
    owner="Команда заказа",
    component="delivery-slot-service",
    layer="integration",
    tags=("broken", "delivery", "connection"),
)
def test_delivery_slot_is_reserved(shop, run_context):
    with allure.step("Рассчитать доставку по подтверждённому адресу"):
        quote = shop.delivery_quote("Москва", "ул. Тверская д. 12")
        assert quote["courierAvailable"] is True

    with allure.step("Зарезервировать доступный слот"):
        shop.reserve_delivery_slot("Москва", "ул. Тверская д. 12")


@pytest.mark.api
@pytest.mark.regression
@allure_case(
    "AUTO-SHOP-057",
    "Для удалённого города предлагается пункт выдачи",
    "Проверяет альтернативный способ получения при недоступности курьера.",
    feature="Оформление заказа",
    story="Доставка и подтверждение",
    severity=allure.severity_level.CRITICAL,
    owner="Команда заказа",
    component="delivery-routing-service",
    layer="api",
    tags=("delivery", "pickup"),
)
def test_remote_city_has_pickup_alternative(shop, run_context):
    with allure.step("Рассчитать доставку в Норильск"):
        quote = shop.delivery_quote("Норильск", "Ленинский проспект д. 21")
        attach_json("Предложение доставки", quote)

    with allure.step("Проверить альтернативу"):
        assert quote["courierAvailable"] is False
        assert quote["alternative"] == "Доставка в пункт выдачи"
