import json
import os
import random
import time

import allure
import pytest

from shop_backend import DemoOnlineStore


@pytest.fixture
def shop():
    return DemoOnlineStore()


@pytest.fixture
def run_context():
    context = {
        "environment": os.getenv("SHOP_DEMO_ENV", "stage"),
        "release": os.getenv("SHOP_DEMO_RELEASE", "2026.08-store-rc1"),
        "pipeline": os.getenv("CI_PIPELINE_URL", "local-run"),
        "commit": os.getenv("CI_COMMIT_SHORT_SHA", "local"),
    }
    allure.dynamic.parent_suite("GitLab CI")
    allure.dynamic.suite("Автоматизированные проверки интернет-магазина")
    allure.dynamic.label("environment", context["environment"])
    allure.dynamic.label("release", context["release"])
    allure.dynamic.parameter("Окружение", context["environment"])
    allure.dynamic.parameter("Релиз", context["release"])
    allure.attach(
        json.dumps(context, ensure_ascii=False, indent=2),
        name="Контекст запуска",
        attachment_type=allure.attachment_type.JSON,
    )
    return context


@pytest.fixture
def demo_delay():
    def wait(reason: str) -> float:
        seconds = float(os.getenv("SHOP_DEMO_DELAY_SECONDS", "5"))
        allure.attach(
            f"Задержка: {seconds:.1f} сек.\nПричина: {reason}",
            name="Параметры ожидания",
            attachment_type=allure.attachment_type.TEXT,
        )
        time.sleep(seconds)
        return seconds

    return wait


@pytest.fixture
def flaky_demo_check():
    mode = os.getenv("SHOP_DEMO_FLAKY", "auto").casefold()

    def check(message: str, *, subsystem: str) -> None:
        if mode == "pass":
            sample = 0.99
        elif mode == "fail":
            sample = 0.01
        elif mode == "auto":
            sample = random.SystemRandom().random()
        else:
            raise ValueError("SHOP_DEMO_FLAKY должен быть auto, pass или fail")

        diagnostics = {
            "subsystem": subsystem,
            "mode": mode,
            "sample": round(sample, 4),
            "failureProbability": 0.4,
            "failureThreshold": 0.4,
        }
        allure.attach(
            json.dumps(diagnostics, ensure_ascii=False, indent=2),
            name="Диагностика нестабильности",
            attachment_type=allure.attachment_type.JSON,
        )
        assert sample >= 0.4, message

    return check
