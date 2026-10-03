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
como CT012–CT015 (`make zerar-dados`), depois de Dados Pessoais (CT010)
e Privacidade (CT011); o teste de API foi renumerado de CT038 para
CT016.

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
