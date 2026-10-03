# Briefing — Continuidade do projeto (próximas telas)

## Objetivo

Dar sequência à suíte de automação iOS do ifPontoCell cobrindo as telas que
ainda faltam — Espelho de Ponto, Holerite, Informe de Rendimento, Férias,
Assinatura do Espelho, e outras que forem surgindo — mantendo o mesmo nível
de tratamento diagnóstico de erro já estabelecido em Login/Onboarding.

Este documento existe pra servir de ponto de partida em uma sessão nova
(inclusive de IA) sem precisar re-explicar o que já foi decidido.

## Estado atual do projeto

- Stack: pytest + Appium (XCUITest), Page Object Model, Python.
- Páginas em `pages/`, todas herdando de `BasePage`: `LoginPage`,
  `OnboardingPage`, `UnlockPage`, `HomePage`, `MenuPage`, `SettingsPage`,
  `AutorizacaoPage`.
- `BasePage` centraliza waits, clique, digitação, logging e visibilidade.
  Timeouts padronizados em `config/timeouts.py`: `SHORT_TIMEOUT=2`,
  `DEFAULT_TIMEOUT=5`, `LONG_TIMEOUT=8`, `OPTIONAL_POPUP_TIMEOUT=1`,
  `MAX_TIMEOUT=10`.
- `tests/support/flows.py` — composição de fluxos reutilizáveis (onboarding,
  login, unlock, primeiro acesso). É aqui que entram as checagens ativas de
  popup do caminho feliz.
- `tests/support/assertions.py` — validações compartilhadas do caminho
  negativo (onde o popup É esperado).
- `utils/exceptions.py` — exceções de domínio: `AppAutomationError` (base,
  carrega `tela`/`elemento`/`acao`), `LoginRejeitadoInesperado`,
  `SistemaRejeitadoInesperado`, `ConexaoIndisponivel`, `AlertaInesperado`.
- `api/ifponto_api_client.py` — `IfPontoApiClient`, `MonitorCelularClient`,
  `ConfiguracaoApp*`. Hoje usado só pro paliativo de ativação de celular no
  primeiro acesso; não existe validação de dado de teste via API ainda.
- Cobertura de testes hoje: onboarding, login (tratamento diagnóstico
  completo), unlock (falta `test_pin_invalido`, já sinalizado como TODO no
  próprio arquivo), e2e (primeiro acesso), registro de ponto.

## Padrão de tratamento de erro (aplicar às telas novas)

1. **Postcondition positiva > inferência por ausência.** Depois de uma ação
   que deveria dar certo, checar ATIVAMENTE se apareceu popup de erro — não
   inferir por timeout genérico.
2. **A checagem ativa entra no fluxo composto do caminho feliz**
   (`flows.py`), nunca nos wrappers primitivos (`_click`/`_type`) nem no
   método que o teste negativo também usa — senão o teste negativo quebra.
3. **Timeout curto pro caminho feliz, longo pro caminho negativo.**
   `OPTIONAL_POPUP_TIMEOUT` (1s) nas checagens especulativas de sucesso
   (onde o popup normalmente NÃO aparece). `DEFAULT_TIMEOUT` (5s) só nas
   validações do caminho negativo, onde o popup É esperado e precisa de
   tempo pra renderizar.
4. **`is_displayed`/`visibility_of_element_located` com poll > presença
   crua.** Presença na árvore não implica visível no XCUITest.
5. **Exceção de domínio, não exceção nativa.** `AppAutomationError` e
   subclasses — mensagem inclui dados relevantes (nunca senha ou dado
   sensível) e um checklist de causas prováveis.
6. **Alerta genérico como fallback, não uma exceção nova por popup.**
   Quando aparece um popup desconhecido (mesmo componente visual
   "ifPontoCell" + botão "OK", mensagem sem locator específico), já existe
   `BasePage._obter_texto_desconhecido_do_alerta()` pra capturar o texto
   real em vez de erro mudo. Reaproveitar nas telas novas — só cadastrar o
   locator específico depois que o popup se repetir e valer a pena nomear.
7. **Locators: accessibility ID técnico sempre que disponível.**
   `IOS_PREDICATE` textual só como fallback documentado com `TODO`,
   sinalizando pro dev que falta setar o ID.

## Telas pendentes (próximo escopo)

- Espelho de Ponto
- Holerite
- Informe de Rendimento
- Férias
- Assinatura do Espelho
- (lista aberta — outras telas do menu lateral que ainda não têm Page Object)

## Pendências a confirmar antes de codar cada tela nova

Mesma lógica da rodada de login — sondar empiricamente, não assumir:

1. **Accessibility IDs reais** — capturar no Appium Inspector antes de
   escrever locator. Se não tiver `accessibilityIdentifier` setado, usar o
   que tiver disponível e sinalizar ao dev que falta.
2. **Fluxo de navegação até a tela** — a partir de onde (menu lateral,
   Home)? Precisa de dado prévio (ex.: já ter registrado ponto) pra a tela
   ter conteúdo?
3. **Estados de erro conhecidos da tela** — período sem dado, falha de
   rede, arquivo indisponível (holerite/informe de rendimento costumam vir
   de PDF gerado no backend — pode ter estado de "ainda não disponível").
4. **Existe validação via API** pra esses dados (comparar o que a UI mostra
   com o que a API retorna)? Só vale a pena se for barato — mesmo critério
   já usado antes.
5. **Ações que alteram estado** (ex.: "Assinatura do Espelho" provavelmente
   assina/confirma algo de forma irreversível) — checar se o app tem
   confirmação prévia, e se dá pra desfazer no ambiente de teste.

## Fluxo de trabalho estabelecido nesta sessão

- **Git:** squash merge da feature pro `desenvolvimento`, feito a partir da
  máquina/conta que deve aparecer como autora oficial do commit:
  ```bash
  git checkout desenvolvimento && git pull origin desenvolvimento
  git merge --squash feature/<nome> && git commit -m "..."
  git push origin desenvolvimento
  ```
- `make delete-branch` agora recusa apagar branch não mesclada (não força
  mais silenciosamente). Depois de um squash merge, a branch não é
  reconhecida como "mesclada" pelo Git — usar `git branch -D` manualmente
  nesse caso específico.
- **Troubleshooting de ambiente:** `RESET_AMBIENTE.md` /
  `Makefile.reset.mk`. Alvos rodam com `make -f Makefile.reset.mk <alvo>`
  (não incluído no Makefile principal).
- **Validar de verdade antes de confiar na mudança.** Nesta sessão as
  mudanças de código só foram validadas por `py_compile`/leitura — sem
  `pytest` instalado na máquina usada. Rodar `make login` (ou o teste
  relevante) contra um driver real é o próximo passo obrigatório antes de
  dar como fechado.

## Fora de escopo (por enquanto)

- Refatorar report/WeasyPrint — já funcional e documentado.
- `test_pin_invalido` — TODO já existente em `test_unlock.py`, não é
  bloqueante pro que vier a seguir.
- Trocar locators textuais por accessibility ID técnico — só quando o dev
  disponibilizar.
