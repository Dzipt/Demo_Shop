import allure
import pytest

from helpers import attach_json, test_case as allure_case


pytestmark = [pytest.mark.testops_demo]


@pytest.mark.api
@pytest.mark.regression
@allure_case(
    "AUTO-SHOP-016",
    "Поиск нормализует регистр запроса",
    "Проверяет, что изменение регистра не влияет на поиск товара по модели.",
    feature="Каталог и поиск",
    story="Поиск и фильтрация",
    severity=allure.severity_level.NORMAL,
    owner="Команда каталога",
    component="catalog-search-api",
    layer="api",
    tags=("search", "normalization"),
)
def test_search_is_case_insensitive(shop, run_context):
    with allure.step("Выполнить поиск модели в верхнем регистре"):
        result = shop.search("THINKPAD")
        attach_json("Результаты поиска", result)

    with allure.step("Проверить найденную модель"):
        assert [item["sku"] for item in result] == ["LAP-LENOVO-T14"]


@pytest.mark.api
@pytest.mark.regression
@allure_case(
    "AUTO-SHOP-017",
    "Поиск удаляет лишние пробелы из запроса",
    "Проверяет нормализацию пользовательского ввода перед обращением к индексу.",
    feature="Каталог и поиск",
    story="Поиск и фильтрация",
    severity=allure.severity_level.NORMAL,
    owner="Команда каталога",
    component="catalog-search-api",
    layer="api",
    tags=("search", "normalization"),
)
def test_search_trims_repeated_spaces(shop, run_context):
    with allure.step("Отправить запрос с лишними пробелами"):
        result = shop.search("   airpods   ")

    with allure.step("Проверить выдачу"):
        assert len(result) == 1
        assert result[0]["sku"] == "HDP-APPLE-PRO2"


@pytest.mark.api
@pytest.mark.regression
@allure_case(
    "AUTO-SHOP-018",
    "Фильтр бренда исключает товары других производителей",
    "Проверяет совместную работу текстового поиска и фильтра бренда.",
    feature="Каталог и поиск",
    story="Поиск и фильтрация",
    severity=allure.severity_level.CRITICAL,
    owner="Команда каталога",
    component="catalog-search-api",
    layer="api",
    tags=("search", "brand-filter"),
)
def test_brand_filter_excludes_other_products(shop, run_context):
    with allure.step("Найти наушники бренда Sony"):
        result = shop.search("наушники", brand="Sony")
        attach_json("Отфильтрованная выдача", result)

    with allure.step("Проверить бренд каждого товара"):
        assert result
        assert {item["brand"] for item in result} == {"Sony"}


@pytest.mark.api
@pytest.mark.known_defect
@allure_case(
    "AUTO-SHOP-019",
    "Точное совпадение модели находится выше аксессуаров",
    "Проверяет релевантность поиска. Дефект SHOP-844 ранжирует дешёвый аксессуар выше самого товара.",
    feature="Каталог и поиск",
    story="Поиск и фильтрация",
    severity=allure.severity_level.NORMAL,
    owner="Команда каталога",
    component="catalog-search-api",
    layer="api",
    tags=("known-defect", "search", "ranking"),
)
def test_exact_product_match_is_ranked_before_accessories(shop, run_context):
    with allure.step("Найти точную модель наушников"):
        result = shop.search("Sony WH-1000XM5")
        attach_json("Порядок выдачи", result)

    with allure.step("Проверить первый результат"):
        assert result[0]["sku"] == "HDP-SONY-XM5", (
            "SEARCH-RANKING-MISMATCH: аксессуар расположен выше точного "
            "совпадения модели [SHOP-844]"
        )


@pytest.mark.api
@pytest.mark.regression
@allure_case(
    "AUTO-SHOP-020",
    "Поиск неизвестного товара возвращает пустую выдачу",
    "Проверяет корректный пустой ответ вместо ошибки каталога.",
    feature="Каталог и поиск",
    story="Поиск и фильтрация",
    severity=allure.severity_level.NORMAL,
    owner="Команда каталога",
    component="catalog-search-api",
    layer="api",
    tags=("search", "empty-result"),
)
def test_unknown_product_returns_empty_result(shop, run_context):
    with allure.step("Найти отсутствующую модель"):
        result = shop.search("DemoPhone Ultra 99")

    with allure.step("Проверить пустой ответ"):
        assert result == []


@pytest.mark.api
@pytest.mark.regression
@allure_case(
    "AUTO-SHOP-021",
    "Служебный поиск может показать товар без остатка",
    "Проверяет выдачу отсутствующего товара при отключенном фильтре наличия.",
    feature="Каталог и поиск",
    story="Поиск и фильтрация",
    severity=allure.severity_level.NORMAL,
    owner="Команда каталога",
    component="catalog-availability",
    layer="api",
    tags=("search", "stock"),
)
def test_out_of_stock_product_can_be_requested_explicitly(shop, run_context):
    with allure.step("Запросить товар без фильтра наличия"):
        result = shop.search("Xiaomi 14", in_stock=False)

    with allure.step("Проверить остаток найденного товара"):
        assert len(result) == 1
        assert result[0]["stock"] == 0


@pytest.mark.api
@pytest.mark.smoke
@allure_case(
    "AUTO-SHOP-022",
    "Карточка товара доступна по точному SKU",
    "Проверяет получение опубликованной карточки товара по идентификатору.",
    feature="Каталог и поиск",
    story="Карточка товара",
    severity=allure.severity_level.CRITICAL,
    owner="Команда каталога",
    component="product-card-api",
    layer="api",
    tags=("product-card", "smoke"),
)
def test_product_card_is_loaded_by_sku(shop, run_context):
    with allure.step("Открыть карточку iPhone"):
        card = shop.get_product_card("PHN-APPLE-15")
        attach_json("Карточка товара", card)

    with allure.step("Проверить идентификатор и публикацию"):
        assert card["sku"] == "PHN-APPLE-15"
        assert card["published"] is True


@pytest.mark.api
@pytest.mark.regression
@allure_case(
    "AUTO-SHOP-023",
    "Неизвестный SKU возвращает диагностическую ошибку каталога",
    "Проверяет понятный код ошибки при обращении к отсутствующей карточке.",
    feature="Каталог и поиск",
    story="Карточка товара",
    severity=allure.severity_level.NORMAL,
    owner="Команда каталога",
    component="product-card-api",
    layer="api",
    tags=("product-card", "validation"),
)
def test_unknown_sku_returns_catalog_error(shop, run_context):
    with allure.step("Запросить отсутствующий SKU"):
        with pytest.raises(ValueError, match="CATALOG-404") as error:
            shop.get_product_card("LAP-DEMO-404")

    with allure.step("Сохранить диагностическое сообщение"):
        allure.attach(str(error.value), "Ошибка каталога", allure.attachment_type.TEXT)


@pytest.mark.api
@pytest.mark.regression
@allure_case(
    "AUTO-SHOP-024",
    "Цена в карточке передаётся с двумя знаками после запятой",
    "Проверяет денежный формат цены для витрины и внешних потребителей API.",
    feature="Каталог и поиск",
    story="Карточка товара",
    severity=allure.severity_level.CRITICAL,
    owner="Команда каталога",
    component="product-card-api",
    layer="api",
    tags=("product-card", "price"),
)
def test_product_card_price_has_money_format(shop, run_context):
    with allure.step("Получить карточку товара"):
        card = shop.get_product_card("HDP-SONY-XM5")

    with allure.step("Проверить формат цены"):
        whole, fraction = card["price"].split(".")
        assert whole.isdigit()
        assert len(fraction) == 2


@pytest.mark.api
@pytest.mark.regression
@allure_case(
    "AUTO-SHOP-025",
    "Карточка содержит гарантийный срок товара",
    "Проверяет обязательную характеристику для гарантийного обслуживания.",
    feature="Каталог и поиск",
    story="Карточка товара",
    severity=allure.severity_level.CRITICAL,
    owner="Команда каталога",
    component="product-card-api",
    layer="api",
    tags=("product-card", "specifications"),
)
def test_product_card_contains_warranty(shop, run_context):
    with allure.step("Открыть карточку ноутбука"):
        card = shop.get_product_card("LAP-LENOVO-T14")

    with allure.step("Проверить гарантию"):
        assert card["specifications"]["Гарантия"] == "3 года"


@pytest.mark.api
@pytest.mark.known_defect
@allure_case(
    "AUTO-SHOP-026",
    "Галерея товара загружается из media-service",
    "Проверяет доступность медиаконтента. Таймаут media-service приводит к Broken.",
    feature="Каталог и поиск",
    story="Карточка товара",
    severity=allure.severity_level.NORMAL,
    owner="Команда каталога",
    component="product-media-service",
    layer="integration",
    tags=("broken", "product-card", "timeout"),
)
def test_product_card_contains_gallery(shop, run_context):
    with allure.step("Открыть карточку товара"):
        card = shop.get_product_card("PHN-SAMSUNG-S24")
        assert card["published"] is True

    with allure.step("Загрузить галерею из media-service"):
        shop.get_product_media(card["sku"])


@pytest.mark.api
@pytest.mark.flaky
@allure_case(
    "AUTO-SHOP-027",
    "Остатки в поисковом индексе синхронизированы с каталогом",
    "Проверяет асинхронную репликацию остатков. Индекс отстаёт с вероятностью 40%.",
    feature="Каталог и поиск",
    story="Карточка товара",
    severity=allure.severity_level.CRITICAL,
    owner="Команда каталога",
    component="catalog-availability",
    layer="api",
    tags=("flaky", "stock", "eventual-consistency"),
)
def test_catalog_stock_is_never_negative(shop, run_context, flaky_demo_check):
    with allure.step("Получить остатки каталога"):
        stocks = {sku: product.stock for sku, product in shop.products.items()}
        attach_json("Остатки", stocks)

    with allure.step("Дождаться обновления поискового индекса"):
        flaky_demo_check(
            "CATALOG-STOCK-LAG: остаток SKU PHN-XIAOMI-14 не обновился "
            "в поисковом индексе за 5 секунд [SHOP-856]",
            subsystem="catalog-stock-indexer",
        )

    with allure.step("Проверить значения"):
        assert all(stock >= 0 for stock in stocks.values())


@pytest.mark.api
@pytest.mark.regression
@allure_case(
    "AUTO-SHOP-028",
    "SKU уникальны в каталоге",
    "Проверяет отсутствие конфликтующих идентификаторов товарных карточек.",
    feature="Каталог и поиск",
    story="Карточка товара",
    severity=allure.severity_level.BLOCKER,
    owner="Команда каталога",
    component="catalog-storage",
    layer="integration",
    tags=("catalog", "data-quality"),
)
def test_catalog_skus_are_unique(shop, run_context):
    with allure.step("Собрать SKU товарных карточек"):
        skus = [product.sku for product in shop.products.values()]

    with allure.step("Проверить уникальность"):
        assert len(skus) == len(set(skus))


@pytest.mark.api
@pytest.mark.known_defect
@allure_case(
    "AUTO-SHOP-029",
    "Галерея флагманского смартфона содержит шесть изображений",
    "Проверяет полноту медиаконтента. Известный дефект SHOP-732: одно изображение не публикуется.",
    feature="Каталог и поиск",
    story="Карточка товара",
    severity=allure.severity_level.NORMAL,
    owner="Команда каталога",
    component="product-media-service",
    layer="integration",
    tags=("known-defect", "media"),
)
def test_flagship_product_has_complete_gallery(shop, run_context):
    with allure.step("Открыть карточку флагманского смартфона"):
        card = shop.get_product_card("PHN-APPLE-15")
        attach_json("Данные галереи", {"sku": card["sku"], "images": card["galleryImages"]})

    with allure.step("Проверить согласованное количество изображений"):
        assert card["galleryImages"] == 6, (
            "PRODUCT-MEDIA-INCOMPLETE: опубликовано 5 из 6 изображений [SHOP-732]"
        )
