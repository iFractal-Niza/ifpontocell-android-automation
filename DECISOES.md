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

## Ativação do celular: emulador como o simulador

**Data:** 2026-10-03

`flows._ativar_celular_antes_unlock` segue a regra do iOS trocando
simulador por emulador: no emulador, espera o registro de celular novo e
o ativa pela API; no celular real, não espera nem ativa, só marca
`sem_foto` no registro mais recente. A ativação é idempotente (registro
já ativo não é reativado).

**A confirmar na primeira execução:** no iOS, só o simulador sobe com o
celular desativado. Se no Android o celular real também subir desativado,
ou se o emulador reaproveitar o registro (mesmo `ANDROID_ID` depois de
reinstalar), ajustar essa regra.

---

## PIN: teclado comum à criação, à confirmação e ao desbloqueio

**Data:** 2026-10-03

O projeto Android de referência não tem marcador exclusivo de cada etapa
do PIN: o teclado `numberN` aparece na criação, na confirmação e no
desbloqueio; só o `relative_first_access` marca o desbloqueio.

- `UnlockPage` usa a digitação robusta do iOS (toca o mesmo dígito até a
  tela mudar, até 6 toques), com o teclado como marcador: a criação
  termina com o teclado ainda na tela; a confirmação, quando ele some.
  Por isso o `APP_PIN` precisa ser um dígito repetido (ex.: `1111`).
- Em `flows.etapa_do_primeiro_acesso`, a etapa "logado" é sondada antes
  de "criar PIN": senão a tela de desbloqueio seria lida como criação.

Textos ou ids próprios de cada etapa devolveriam a conferência que o iOS
faz (PENDENCIAS_LOCATORS_ANDROID.md).

---

## Onboarding: o mesmo botão em duas telas

**Data:** 2026-10-03

`BOTAO_PROXIMO_BOAS_VINDAS` e `BOTAO_INICIAR_CONFIGURACAO` são o mesmo
resource-id (`btn_confirmar_informacao`). O `_passar_pelo_boas_vindas`
do iOS (toca PRÓXIMO até a tela seguinte, até 4 vezes) sai no primeiro
toque, e o `preparar_fluxo_inicial` toca de novo como "iniciar
configuração" — o comportamento que o Android já tinha. Um unitário
documenta isso.

---

## Autorização do aparelho não é sondada

**Data:** 2026-10-03

A `AutorizacaoPage` veio completa do iOS (retry de bloqueio/liberação,
modal de aparelho inativo), mas os fluxos Android não a sondam: a tela
não existe na build de referência, e as duas checagens do
`garantir_tela_login` do iOS custariam 2s cada, sempre. Se a build voltar
a exibi-la, religar as checagens (ver `garantir_tela_login` no iOS).

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
