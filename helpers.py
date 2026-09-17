import csv
import io
import json

import allure


def attach_json(name: str, payload: object) -> None:
    allure.attach(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        name=name,
        attachment_type=allure.attachment_type.JSON,
    )


def attach_csv(name: str, rows: list[list[object]]) -> None:
    stream = io.StringIO()
    csv.writer(stream).writerows(rows)
    allure.attach(
        stream.getvalue(),
        name=name,
        attachment_type=allure.attachment_type.CSV,
    )


def test_case(
    external_id: str,
    title: str,
    description: str,
    *,
    feature: str,
    story: str,
    severity,
    owner: str,
    component: str,
    layer: str,
    tags: tuple[str, ...],
):
    """Apply the common TestOps metadata without hiding the test scenario itself."""

    decorators = (
        allure.label("external_id", external_id),
        allure.title(title),
        allure.description(description),
        allure.epic("Интернет-магазин"),
        allure.feature(feature),
        allure.story(story),
        allure.severity(severity),
        allure.label("owner", owner),
        allure.label("component", component),
        allure.label("layer", layer),
        allure.tag(*tags),
    )

    def decorate(function):
        for apply_decorator in reversed(decorators):
            function = apply_decorator(function)
        return function

    return decorate
