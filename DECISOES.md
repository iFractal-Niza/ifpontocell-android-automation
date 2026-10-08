# Decisões de arquitetura

Registro de decisões que não são óbvias só de ler o código — principalmente
onde o Android diverge do projeto irmão `ifpontocell-ios-automation`, de
onde vem a arquitetura. As decisões herdadas sem mudança (configuração
tipada, sessão morna, primeiro acesso em corrente, CTs no próprio teste,
status do report, pages por menu...) estão no `DECISOES.md` do iOS.

---

## Refatoração para a arquitetura do iOS

**Data:** 2026-10-03

**Contexto:** o Android nasceu de um snapshot do iOS de 18/08/2026 (commit
`7943b98` do iOS) migrado para UiAutomator2. Desde então o iOS evoluiu
bastante (configuração tipada, env por aparelho, fixtures por assunto,
pages por menu, unitários, report com histórico e vídeo, sessão morna,
primeiro acesso em corrente).

**Como foi feito:** merge de três vias por arquivo (`git merge-file`):
base = iOS `7943b98`, nossa = Android, deles = iOS atual. A evolução do iOS
entrou sem perder as adaptações Android; os conflitos (camada de
plataforma e locators) foram resolvidos à mão. O estado anterior está no
primeiro commit da `main`.

**Escopo:** arquitetura + as telas que o Android já tinha (onboarding,
login, unlock, autorização, Home, menus, Ajustes) e o Zerar Dados, que o
primeiro acesso em corrente usa. As telas novas do iOS (Holerite, Informe,
Assinatura do Espelho, Ponto, Status, Estado de Humor, Privacidade, Sobre,
Dados Pessoais, Alterar Senha/PIN) ficam para depois, quando houver os
resource-ids; os unitários delas não vieram.

---

## Um env por aparelho: emulador e celular

**Data:** 2026-10-03

Como no iOS (lá: simulador e iPhone): `config/env.emulator.yaml` (padrão)
e `config/env.real.yaml` (`make ... DEVICE=real`), com templates
`*.example.yaml` de chaves iguais (um unitário confere). Saíram o
`config/env.yaml`, o `env.example.yaml` e os alvos `make set-simulator` /
`make set-real`, que editavam o env para trocar de alvo.

**`ANDROID_SYSTEM_PORT`:** o servidor UiAutomator2 de cada sessão usa uma
porta do Mac (padrão 8200). Dois aparelhos no mesmo Appium com a mesma
porta derrubam a sessão um do outro — o mesmo problema da porta do
WebDriverAgent no iOS (8100 e 8101). Templates: 8200 no emulador, 8201 no
celular.

---

## Popups oportunistas não são suprimidos

**Data:** 2026-10-03

No iOS, "Opinião"/"Melhoria", o alerta de atualização e o lembrete do
primeiro acesso são suprimidos por launch argument (`NSArgumentDomain`).
O Android não tem equivalente: suprimir exigiria gravar as chaves em
`shared_prefs/` antes do launch (só em build debuggable) ou uma flag de
debug do app lida de intent extra (`appium:optionalIntentArguments`) — a
opção mais limpa, depende do time de dev.

**Consequências:**
- `LaunchProfile` não tem `arguments` nem captura simulada (só
  `cold_start`, `manter_estado` e `permissions`); o marker `fake_capture`
  saiu.
- O marker `exibir_lembrete` continua registrado, por paridade, mas não
  muda nada: o lembrete sempre aparece depois do login.
- `HomePage.HOME_STABILITY_TIMEOUT` continua em 4s (no iOS caiu para
  1,5s justamente pela supressão).

---

## Celular sobe ativo: sem ativação pela API

**Data:** 2026-10-03

No iOS, o celular do simulador sobe desativado e o primeiro acesso o
ativa pela API antes do PIN (`_ativar_celular_antes_unlock`, que espera
o registro novo ignorando os códigos de antes do login). No Android o
celular sobe **ativo**, no emulador e no celular (confirmado pelo
Alessandro).

`flows._marcar_sem_foto_antes_unlock` só marca `sem_foto` no registro de
comunicação mais recente — o mesmo que o iOS faz no iPhone. Sem a
ativação, saíram os `codigos_anteriores` e o `reaproveita_celular` da
corrente do primeiro acesso; o `estado_primeiro_acesso` continua (vazio)
para as funções da corrente terem a mesma assinatura do iOS.

---

## PIN: teclado comum à criação, à confirmação e ao desbloqueio

**Data:** 2026-10-03

O projeto Android de referência não tem marcador exclusivo de cada etapa
do PIN: o teclado `numberN` aparece na criação, na confirmação e no
desbloqueio, todos no mesmo contêiner (`relative_first_access`, também
do boas-vindas). O que separa as telas é a instrução (`text_instrucao`):
"Crie uma senha de 4 digitos" na criação e "Entre com sua senha" no
desbloqueio, e "Entre novamente para confirmar" na confirmação
(Inspector, 2026-10-03; no iOS é "Repita a senha").

- `UnlockPage` usa a digitação robusta do iOS (toca o mesmo dígito até a
  tela mudar, até 6 toques): a criação termina quando aparece a
  instrução da confirmação; a confirmação, quando ela some. Por isso o
  `APP_PIN` precisa ser um dígito repetido (ex.: `1111`).
- Em `flows.etapa_do_primeiro_acesso`, criação, confirmação e
  desbloqueio vão pela instrução.

Textos ou ids próprios de cada etapa devolveriam a conferência que o iOS
faz (PENDENCIAS_LOCATORS_ANDROID.md).

---

## Onboarding: telas pelo contêiner

**Data:** 2026-10-03

O botão de avançar é o mesmo resource-id no boas-vindas e nas
informações importantes (`btn_confirmar_informacao`), e o título
"Configurar Aplicativo" é o mesmo nas telas de sistema e de login. Cada
tela tem, porém, um contêiner próprio (`relative_information`,
`relative_system_access`, `relative_login_access`), e é por ele que a
`OnboardingPage` e o `flows.etapa_do_primeiro_acesso` reconhecem a tela.
Exceção: o `relative_first_access` é dividido pelo boas-vindas e pela
criação do PIN — o boas-vindas vai pelo título ("bem-vindo") e a criação
pela instrução ("Crie uma senha de 4 digitos"). Com isso, o `_passar_pelo_boas_vindas` do iOS (toca
PRÓXIMO até a tela seguinte, até 4 vezes) funciona igual.

O diálogo genérico do app (`linear_dialog_geral`: `titulo`, `mensagem`,
`btnDireito`) fica na `BasePage` (`DIALOGO_APP_*`). O texto de um alerta
desconhecido é lido do id `mensagem`; o iOS varria os textos visíveis, o
que no Android pegaria a tela atrás do diálogo.

---

## Autorização do aparelho não é sondada

**Data:** 2026-10-03

A `AutorizacaoPage` veio completa do iOS (retry de bloqueio/liberação,
modal de aparelho inativo), mas os fluxos Android não a sondam: a tela
não existe na build de referência, e as duas checagens do
`garantir_tela_login` do iOS custariam 2s cada, sempre. Se a build voltar
a exibi-la, religar as checagens (ver `garantir_tela_login` no iOS).

---

## App já instalado (`APP_SOURCE=package`) por padrão

**Data:** 2026-10-03

No Android a suíte não instala APK: usa o app já instalado no device
(`APP_SOURCE=package`, padrão do `Settings` e dos templates). O primeiro
acesso parte do app limpo pelo `noReset=false` (o Appium faz `pm clear`),
sem desinstalar. `APP_SOURCE=apk` continua disponível (desinstala pelo
`adb` e o Appium instala o APK de `APP_PATH`).

A versão do app no cabeçalho do report vem do device
(`adb shell dumpsys package`) com `package`, e do APK (`aapt`) com `apk`.

---

## Apagar dados: um diálogo para os dois caminhos

**Data:** 2026-10-03

O ZERAR DADOS do menu do perfil e o APAGAR DADOS DO APLICATIVO dos
Ajustes abrem o mesmo diálogo (`linearApagarDadosDoApp`); no iOS são
componentes diferentes. O `test_zerar_dados.py` mantém o par NÃO/SIM
dos dois caminhos, como no iOS (o SIM pode estar ligado a outra rotina),
como CT034–CT037 (`make zerar-dados`).

---

## Privacidade: a árvore só traz o que está na tela

**Data:** 2026-10-03

A lógica do iOS foi mantida (índice entre "Índice" e o primeiro texto
repetido; tocar o item e conferir a seção). Particularidade: no Android a
árvore só traz o que está na tela, e o item do índice que rolou para fora
some dela; no iOS ficavam as duas ocorrências e a seção era a última.
`secao_esta_visivel` passa a tomar a última ocorrência que não é item do
índice (id `indice_*`; a seção tem o id sem o prefixo). O item 2 do
índice é "Ciclo de vida dos dados" no Android (iOS: "Vida dos Dados").

---

## Todos os testes do iOS, com a mesma numeração de CT

**Data:** 2026-10-03

A suíte Android tem os mesmos testes do iOS, na mesma ordem (`APP_SUITE`
do Makefile) e com os mesmos números de CT (CT001–CT038): um CT é o mesmo
caso nos dois projetos. As telas trazidas por último (Status, Ponto,
geo, Holerite, Informe, Estado de Humor, Assinatura do Espelho, Sobre,
Alterar PIN e Senha do sistema) mantêm a lógica do iOS; os locators sem
equivalente conhecido são `android_pendente("...")`, que nunca casa e
mostra na falha o que falta capturar (PENDENCIAS_LOCATORS_ANDROID.md).

Dependências do iOS que provavelmente mudam com o XML: a aba STATUS e a
Assinatura do Espelho leem dados (dia, código, período) do **nome da
célula**; no Android, ids de item costumam ser fixos.

---

## Alterar PIN: confirmação divergente reseta a troca

**Data:** 2026-10-03

No iOS, repetir um PIN diferente do novo mostra "Confirmação de senha
não conferem / Favor tentar novamente" e continua esperando o PIN. No
Android (confirmado pelo Alessandro), o app reseta a troca e volta a
pedir a senha atual. `AlterarPinPage.repeticao_divergente_recusada`
aceita também essa volta; o CT030 continua dali (o `alterar_pin` já
começa pela senha atual quando ela é pedida).

Sucesso da troca: no Android, um pop-up rápido (sem botão) e o app vai
direto para a Home. O `_concluir_alteracao` do iOS já cobre: toca OK se
houver alerta, volta se ficar na tela e termina ao reconhecer a Home.

---

## Alertas que fecham sozinhos

**Data:** 2026-10-03

No Android, o alerta de sucesso da troca de senha do sistema ("Senha
alterada com sucesso.", mesmo texto do iOS) tem uma barra de tempo e
fecha sozinho, além do OK. `AlertaAppMixin.confirmar_alerta` mantém a
lógica do iOS (o alerta com a mensagem certa tem de aparecer e sumir),
mas toca OK só se ele ainda estiver na tela: o clique do iOS esperava o
OK e dava timeout quando o alerta já tinha fechado.

---

## Plataforma: equivalentes Android

**Data:** 2026-10-03

| iOS | Android |
|---|---|
| `xcrun simctl uninstall` no cold start | `adb uninstall` (só `APP_SOURCE=apk`; com `package`, o `noReset=false` limpa os dados) |
| `reduceMotion` | `disableWindowAnimation` |
| permissões por `simctl` + relaunch | `autoGrantPermissions` na instalação |
| `mobile: setSimulatedLocation` / `resetSimulatedLocation` | `set_location` / `mobile: resetGeolocation` (celular) |
| vídeo pelo XCTest, ffmpeg de reserva | `start_recording_screen` (adb screenrecord, até 3 min) |
| versão do app pelo `Info.plist` | `aapt dump badging` do APK (sem aapt, omitida) |
| `mobile: type` quando o `send_keys` falha | novo clique + `send_keys` |
| valor do campo em `value`, do switch em `value` | `text` e `checked` |
| voltar pela navBar (id, texto, seta nativa) | texto "VOLTAR" ou `driver.back()` |

---

## Histórico do report removido

**Data:** 2026-10-05

O dashboard deixou de comparar com as execuções anteriores (falhas novas,
recorrentes e instáveis): a seção quase nunca era lida e o report ficou
mais limpo sem ela. Saíram a seção, o `observability/historico.py`, o
`history.json` e o `make limpar-historico`, como na automação iOS. Um
`history.json` antigo que sobre na pasta do report não é mais lido (o
`make clear` o apaga).

---

## Export do report em PDF removido

**Data:** 2026-10-05

Saíram o `make report-pdf`, o `scripts/export_report_pdf.py`, o
`reports/assets/print.css` e o WeasyPrint. O PDF não tinha o que passou a
existir só na página (testes manuais, melhorias, classificação, ficha do
teste) e não era usado: para compartilhar, vale a cópia do **Baixar
HTML**. Para papel, o imprimir do navegador (Cmd+P) segue funcionando.

---

## Report num pacote comum às três automações

**Data:** 2026-10-07

O report (assets, dashboard, colunas da tabela, testes manuais
previstos) era copiado entre as automações iOS, Android e web, e cada
mudança virava três commits; os arquivos já começavam a divergir. Foi
para o pacote **ifponto-observability** (repositório próprio), instalado
pelo `requirements.txt` numa versão fixa (`@v1.0.0`) e registrado como
plugin no `conftest.py` (`qa_observability.tabela`, `qa_observability.testes_manuais`).
Aqui fica o que é da plataforma: captura das evidências (driver do
Appium), vídeo, identificação da execução, métricas e o
`testes_manuais.yaml`. Os testes do report no navegador (antes
`make test-report`) estão no pacote. Um teste daqui falha se o
`pytest_report.py` voltar a ter gancho de tabela (as colunas seriam
trocadas duas vezes).


## Métricas, CTs e evidências também no pacote

**Data:** 2026-10-07

As métricas do dashboard, o catálogo de CTs (leitura, validação,
renumeração), as evidências sob demanda e a pasta do report eram
iguais nas três automações, a não ser por o mapa de fluxos, a ordem da suíte e o print (driver do Appium ou page do Playwright). Foram para o pacote
(`v1.1.0`: `qa_observability.execution_metrics`, `casos_teste`, `evidencias`,
`pastas`), e o que muda fica no `observability/automacao.py`, que o
pacote importa sozinho: as pastas com CT (`tests/app`, `tests/api`), a ordem da suíte (a `APP_SUITE` do Makefile e depois `tests/api`), o nome dos fluxos (`fluxo_por_arquivo`) e o print pelo `driver.save_screenshot`. O `qa_observability.evidencias` também é
plugin: registra o CT de cada teste, que vai na frente do nome do print
das evidências. Os testes daqui conferem só a configuração (fluxos, CTs
únicos, ordem da suíte, print); o resto é testado no pacote.


## O plugin do report também no pacote

**Data:** 2026-10-07

O `observability/pytest_report.py` era igual no iOS e no Android (só o
título mudava) e, na web, igual no esqueleto: nome e pasta do report,
limpeza dos antigos, aviso de pulados, métricas de cada etapa, título com
o CT, erro resumido, evidências, a página e o resumo no terminal. Isso
virou o plugin `qa_observability.relatorio` (pacote `v1.2.0`). Aqui ficou só
o que é do Appium: achar o driver nas fixtures, o print e a árvore da tela (XML) na falha e o vídeo embutido, em `observability/anexos.py`, ligado pela configuração
(`observability/automacao.py`: `sessao_de`, `na_falha`, `na_etapa`,
`contexto`, título e nota). O `make unit` desliga o report com
`-p no:qa_observability.relatorio`. Os plugins do pacote vêm primeiro no `conftest.py`: o `observability.video` importa o `qa_observability.relatorio` (para achar o driver), e um plugin já importado não teria o assert reescrito pelo pytest. O `video.py` calcula a pasta dos vídeos na hora, não no import.
