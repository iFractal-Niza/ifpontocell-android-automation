"""Helpers de locator Android usados pelos Page Objects.

Mantém os resource-ids independentes do package, reproduzindo a estratégia
já validada no projeto Android de referência.
"""

import json
import re

from appium.webdriver.common.appiumby import AppiumBy


def _resource_id_regex(ids: str) -> str:
    partes = ids.split("|")

    if all(":id/" not in parte for parte in partes):
        return rf"(.*:id/)?({'|'.join(re.escape(p) for p in partes)})"

    alternativas: list[str] = []
    for parte in partes:
        if ":id/" in parte:
            alternativas.append(re.escape(parte))
        else:
            alternativas.append(rf"(.*:id/)?({re.escape(parte)})")

    return rf"({'|'.join(alternativas)})"


def android_id(*ids: str) -> tuple[str, str]:
    """Locator por resource-id, aceitando id curto ou completo."""
    if not ids:
        raise ValueError("Informe ao menos um resource-id.")

    regex = _resource_id_regex("|".join(ids))
    selector = f'new UiSelector().resourceIdMatches({json.dumps(regex)})'
    return AppiumBy.ANDROID_UIAUTOMATOR, selector


def android_text(text: str) -> tuple[str, str]:
    """Locator por texto exato."""
    selector = f'new UiSelector().text({json.dumps(text)})'
    return AppiumBy.ANDROID_UIAUTOMATOR, selector


def android_text_contains(text: str) -> tuple[str, str]:
    """Locator por trecho de texto."""
    selector = f'new UiSelector().textContains({json.dumps(text)})'
    return AppiumBy.ANDROID_UIAUTOMATOR, selector


def android_text_matches(pattern: str) -> tuple[str, str]:
    """Locator por regex de texto."""
    selector = f'new UiSelector().textMatches({json.dumps(pattern)})'
    return AppiumBy.ANDROID_UIAUTOMATOR, selector


def android_description(description: str) -> tuple[str, str]:
    """Locator por content-desc exato."""
    selector = f'new UiSelector().description({json.dumps(description)})'
    return AppiumBy.ANDROID_UIAUTOMATOR, selector


def android_id_prefixo(prefixo: str) -> tuple[str, str]:
    """
    Locator por início do resource-id (como o BEGINSWITH do iOS): para
    itens de lista cujo id termina com um sufixo variável.
    """
    regex = rf"(.*:id/)?{re.escape(prefixo)}.*"
    selector = f"new UiSelector().resourceIdMatches({json.dumps(regex)})"
    return AppiumBy.ANDROID_UIAUTOMATOR, selector


def android_pendente(nome: str) -> tuple[str, str]:
    """
    Locator ainda não capturado no Appium Inspector (trazido do iOS sem
    equivalente Android conhecido). Nunca casa: a falha mostra
    "PENDENTE_<nome>", o que falta capturar
    (PENDENCIAS_LOCATORS_ANDROID.md).
    """
    return android_id(f"PENDENTE_{nome}")
