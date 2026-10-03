# Briefing — Continuidade do projeto (próximas telas)

Ponto de partida para uma sessão nova (inclusive de IA) sem re-explicar o
que já foi decidido.

## Estado atual (2026-10-03)

- Arquitetura igual à do `ifpontocell-ios-automation` (ver README e
  DECISOES.md, "Refatoração para a arquitetura do iOS").
- Telas cobertas: onboarding, login, unlock (PIN), Home e registro de
  ponto sem foto, menus, Ajustes do Aplicativo, Zerar Dados (só o que a
  corrente do primeiro acesso usa).
- Locators: `pages/android_locators.py`; provisórios e pendentes em
  `PENDENCIAS_LOCATORS_ANDROID.md`.

## Telas pendentes — já implementadas no iOS

| Tela | iOS (page / teste) | Pasta Android |
|---|---|---|
| Registro com geo delimitação | `tests/app/test_registro_geo.py` | (Home) |
| Aba STATUS | `pages/status/`, `test_status.py` | `pages/status/` |
| Tela Ponto | `pages/ponto/`, `test_ponto.py` | `pages/ponto/` |
| Holerite / Informe de Rendimentos | `pages/holerite/`, `pages/informe_rendimentos/`, `pages/compartilhado/` | idem |
| Assinatura do Espelho | `pages/ass_espelho/` | `pages/ass_espelho/` |
| Estado de Humor | `pages/estado_humor/` | `pages/estado_humor/` |
| Sobre / Dados Pessoais / Privacidade | `pages/sobre_aplicativo/`, `pages/dados_pessoais/`, `pages/privacidade/` | idem |
| Alterar PIN / Senha do sistema | `pages/alterar_senha/`, `tests/fixtures/pin.py`, `senha_sistema.py` | idem |
| Zerar Dados (teste) e Apagar dados pelos Ajustes | `test_zerar_dados.py`, `pages/ajustes/apagar_dados_page.py` | idem |

## Como portar uma tela

1. Copiar a page, o teste e os unitários do iOS para o mesmo caminho.
2. Trocar os locators iOS (`ACCESSIBILITY_ID`, `IOS_PREDICATE`,
   `IOS_CLASS_CHAIN`) por `android_id(...)` / `android_text(...)`,
   capturados no Appium Inspector — sondagem feita manualmente pelo
   Alessandro.
3. Conferir o que o iOS lê por atributo: `label`/`value` viram `text`
   (switch: `checked`).
4. Registrar o alvo no `Makefile` (variável `TEST_*`, `APP_SUITE`, alvo e
   help) e o plugin de fixture no `conftest.py`, se houver.
5. Locator ainda por texto vai para `PENDENCIAS_LOCATORS_ANDROID.md`;
   diferença de comportamento em relação ao iOS, para o `DECISOES.md`.

## Padrão de tratamento de erro (vale igual ao iOS)

1. **Postcondition positiva > inferência por ausência.** Depois de uma ação
   que deveria dar certo, checar ATIVAMENTE se apareceu popup de erro.
2. **A checagem ativa entra no fluxo composto do caminho feliz**
   (`flows.py`), nunca nos wrappers primitivos (`_click`/`_type`).
3. **Timeout curto pro caminho feliz, longo pro caminho negativo**
   (`OPTIONAL_POPUP_TIMEOUT` x `DEFAULT_TIMEOUT`).
4. **Exceção de domínio, não exceção nativa** (`utils/exceptions.py`), com
   checklist de causas prováveis e sem dado sensível.
5. **Alerta desconhecido** é capturado por
   `BasePage._obter_texto_desconhecido_do_alerta()` em vez de erro mudo.
