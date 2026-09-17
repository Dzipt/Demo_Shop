import allure
import pytest

from helpers import attach_json


pytestmark = [pytest.mark.testops_demo]


@pytest.mark.api
@pytest.mark.smoke
@pytest.mark.parametrize(
    ("query", "brand", "expected_sku"),
    [
        pytest.param("iphone", None, "PHN-APPLE-15", id="iphone"),
        pytest.param("смартфон", "Samsung", "PHN-SAMSUNG-S24", id="samsung"),
        pytest.param("macbook", "Apple", "LAP-APPLE-AIR13", id="macbook"),
        pytest.param("thinkpad", "Lenovo", "LAP-LENOVO-T14", id="thinkpad"),
        pytest.param("наушники", "Sony", "HDP-SONY-XM5", id="sony"),
        pytest.param("airpods", "Apple", "HDP-APPLE-PRO2", id="airpods"),
    ],
)
@allure.label("external_id", "AUTO-SHOP-001")
@allure.title("Поиск возвращает релевантный товар: {query}, бренд {brand}")
@allure.description(
    "Проверяет поиск по русским и латинским запросам с фильтром бренда. "
    "Риск: доступный товар не попадает в выдачу, и покупатель покидает магазин."
)
@allure.epic("Интернет-магазин")
@allure.feature("Каталог и поиск")
@allure.story("Поиск и фильтрация")
@allure.severity(allure.severity_level.CRITICAL)
@allure.label("owner", "Команда каталога")
@allure.label("component", "catalog-search-api")
@allure.label("layer", "api")
@allure.tag("smoke", "search", "parameterized")
def test_product_search_returns_relevant_item(
    shop,
    run_context,
    query,
    brand,
    expected_sku,
):
    with allure.step("Подготовить поисковый запрос"):
        request = {"query": query, "brand": brand, "inStock": True}
        attach_json("Запрос к каталогу", request)

    with allure.step("Получить выдачу каталога"):
        result = shop.search(query, brand=brand, in_stock=True)
        attach_json("Ответ поискового API", result)

    with allure.step("Проверить ожидаемый SKU, наличие и бренд"):
        skus = {item["sku"] for item in result}
        assert expected_sku in skus, (
            f"CATALOG-SEARCH-EMPTY: товар {expected_sku} не найден по запросу "
            f"'{query}', получены SKU: {sorted(skus)}"
        )
        assert all(item["stock"] > 0 for item in result)
        if brand:
            assert all(item["brand"] == brand for item in result)


@pytest.mark.api
@pytest.mark.regression
@allure.label("external_id", "AUTO-SHOP-002")
@allure.title("Товар без остатка скрыт из доступной к заказу выдачи")
@allure.description(
    "Проверяет, что позиция с нулевым остатком не предлагается для покупки, "
    "но остаётся доступной при отключённом фильтре наличия."
)
@allure.epic("Интернет-магазин")
@allure.feature("Каталог и поиск")
@allure.story("Поиск и фильтрация")
@allure.severity(allure.severity_level.NORMAL)
@allure.label("owner", "Команда каталога")
@allure.label("component", "catalog-availability")
@allure.label("layer", "api")
@allure.tag("regression", "stock")
def test_out_of_stock_product_is_hidden_from_available_results(shop, run_context):
    with allure.step("Найти Xiaomi 14 среди доступных товаров"):
        available = shop.search("Xiaomi 14", in_stock=True)
        attach_json("Выдача с фильтром наличия", available)

    with allure.step("Повторить запрос без фильтра наличия"):
        complete = shop.search("Xiaomi 14", in_stock=False)
        attach_json("Полная выдача", complete)

    with allure.step("Проверить правила отображения"):
        assert available == []
        assert [item["sku"] for item in complete] == ["PHN-XIAOMI-14"]
        assert complete[0]["stock"] == 0


@pytest.mark.api
@pytest.mark.smoke
@allure.label("external_id", "AUTO-SHOP-003")
@allure.title("Карточка ThinkPad T14 содержит характеристики выбранной модели")
@allure.description(
    "Сверяет SKU, цену, наличие и ключевые характеристики карточки с эталонной "
    "конфигурацией 32 ГБ / 1 ТБ / чёрный."
)
@allure.epic("Интернет-магазин")
@allure.feature("Каталог и поиск")
@allure.story("Карточка товара")
@allure.severity(allure.severity_level.CRITICAL)
@allure.label("owner", "Команда каталога")
@allure.label("component", "product-card-api")
@allure.label("layer", "api")
@allure.tag("smoke", "product-card")
def test_product_card_matches_selected_model(shop, run_context):
    with allure.step("Открыть карточку товара LAP-LENOVO-T14"):
        card = shop.get_product_card("LAP-LENOVO-T14")
        attach_json("Карточка товара", card)

    with allure.step("Проверить идентификатор, цену и публикацию"):
        assert card["sku"] == "LAP-LENOVO-T14"
        assert card["price"] == "149990.00"
        assert card["stock"] == 4
        assert card["published"] is True
        assert card["galleryImages"] >= 4

    with allure.step("Сверить характеристики выбранного варианта"):
        expected = {
            "Память": "32 ГБ DDR5",
            "Накопитель": "SSD 1 ТБ",
            "Цвет": "Чёрный",
            "Гарантия": "3 года",
        }
        for field, value in expected.items():
            assert card["specifications"][field] == value


@pytest.mark.api
@pytest.mark.flaky
@pytest.mark.slow_demo
@allure.label("external_id", "AUTO-SHOP-004")
@allure.title("Поиск отвечает в пределах установленного SLA")
@allure.description(
    "Контролирует время ответа поискового сервиса. Проверка намеренно воспроизводит "
    "редкие задержки реплики каталога и падает с вероятностью 40%."
)
@allure.epic("Интернет-магазин")
@allure.feature("Каталог и поиск")
@allure.story("Поиск и фильтрация")
@allure.severity(allure.severity_level.CRITICAL)
@allure.label("owner", "Команда каталога")
@allure.label("component", "catalog-search-api")
@allure.label("layer", "integration")
@allure.tag("flaky", "performance", "search")
def test_catalog_search_response_time(
    shop,
    run_context,
    demo_delay,
    flaky_demo_check,
):
    with allure.step("Отправить запрос к поисковому сервису"):
        result = shop.search("наушники", in_stock=True)
        assert result

    with allure.step("Дождаться ответа асинхронной реплики каталога"):
        delay = demo_delay("Имитация длительного запроса для live-обновления запуска")
        attach_json(
            "Метрики поискового запроса",
            {
                "route": "GET /api/v1/catalog/search",
                "demoWallTimeSeconds": delay,
                "slaMilliseconds": 1200,
                "replica": "catalog-read-02",
            },
        )

    with allure.step("Проверить, что сервис уложился в SLA"):
        flaky_demo_check(
            "CATALOG-SEARCH-SLA: p95 ответа достиг 2380 мс при допустимых 1200 мс; "
            "реплика catalog-read-02 отстаёт от основной на 146 событий [SHOP-427]",
            subsystem="catalog-search-latency",
        )
