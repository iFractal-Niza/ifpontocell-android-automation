# Pendências de locators Android

A refatoração reutilizou os `resource-id` disponíveis no projeto Android de referência. Os itens abaixo **não existem naquele projeto** e precisam ser confirmados na build Android atual pelo Appium Inspector.

## Prioridade 1 — necessários para a suíte atual

### 1. Login — botão exibir/ocultar senha

Arquivo: `pages/login_page.py`

Constante:

```python
BOTAO_VER_SENHA
```

Fallback temporário configurado:

```text
btnVerSenha
text_input_end_icon
```

Capturar no Inspector o `resource-id` real do ícone que alterna a visibilidade da senha.

### 2. Ajustes — switch "Lembrete para registro do ponto"

Arquivo: `pages/settings_page.py`

Constante:

```python
SWITCH_LEMBRETE_REGISTRO_PONTO
```

Fallback temporário configurado:

```text
switchLembreteRegistroPonto
switch_lembrete_registro_ponto
```

Esse locator é usado pelo E2E para validar que a opção ativada no popup ficou habilitada em **Ajustes do Aplicativo**.

## Prioridade 2 — usado por cenário/configuração relacionada

### 3. Ajustes — switch "Confirmação de foto"

Arquivo: `pages/settings_page.py`

Constante:

```python
SWITCH_CONFIRMACAO_FOTO
```

Fallback temporário configurado:

```text
switchConfirmacaoFoto
switch_confirmacao_foto
```

O fluxo de registro sem foto atual configura `sem_foto=True` pela API e usa `btn_confirmar_sem_foto`, então esse locator não bloqueia o fluxo principal de marcação.

## Provisórios da refatoração para a arquitetura do iOS (2026-10-03)

Locators que vieram com a lógica nova do iOS e não existem no projeto Android de referência. Estão por texto ou pelo diálogo genérico do app; confirmar no Inspector:

| Page / constante | Provisório | Usado em |
|---|---|---|
| `HomePage.POPUP_ESPELHO_PENDENTE_*` | texto `Assinatura do espelho` / `DEPOIS` / `ASSINAR` | popups ao abrir o app (Home) |
| `HomePage.POPUP_FORA_GEO_*` | texto `Você está fora da geo localização` / `NÃO` / `SIM` | registro de ponto fora da geo |
| `ZerarDadosPage.DIALOGO` / `BOTAO_NAO` / `BOTAO_SIM` | `linear_dialog_geral` + `btnEsquerdo` / `btnDireito` | recomeçar o primeiro acesso (corrente onboarding → e2e) |
| `MenuLateralPage` — `ESTADO DO HUMOR` | texto (sem id técnico) | menu lateral |
| `VoltarParaHomeMixin.BOTAO_VOLTAR_TEXTO` | texto `VOLTAR`, senão `driver.back()` | telas abertas pelo menu |
| `AlertaAppMixin` | texto da mensagem + `OK` | alertas do app |
| `AutorizacaoPage.MODAL_APARELHO_INATIVO` / `BOTAO_OK_MODAL` | texto `Aparelho inativo` / `OK` | só se a tela de autorização existir |

Também ajudariam (não bloqueiam):

- **Onboarding:** um id/texto próprio da tela "informações importantes" — hoje o botão tem o mesmo id do boas-vindas (`btn_confirmar_informacao`), e a repetição de toques do iOS não acontece (DECISOES.md).
- **PIN:** textos ou ids próprios de "Crie uma senha" e "Repita a senha"; e confirmar que `relative_first_access` só aparece no **desbloqueio** (é ele que separa o desbloqueio da criação do PIN em `flows.etapa_do_primeiro_acesso`).

## Fallbacks por texto — funcionais, mas vale trocar por resource-id

O projeto Android de referência não continha IDs técnicos para estes componentes. A refatoração deixou fallback por texto:

- popup de sistema não encontrado (`ifPontoCell`, `Sistema não encontrado.`, `OK`);
- popup de credenciais inválidas (`Usuário e/ou senha inválidos.`, `OK`);
- popup de conexão sem internet;
- popup de lembrete (`ATIVAR` / `DEPOIS`);
- popup de opinião (`Opinião` / `NÃO`);
- popup de atualização (`Tem novidade pra você` / `Cancelar`);
- popup de melhoria (`O que podemos melhorar` / `DEPOIS`);
- títulos de onboarding;
- eventual botão Android `Agora não` após login.

Esses itens **não estão bloqueados**: os testes conseguem procurá-los pelo texto atual. Se houver `resource-id`, vale substituir para reduzir dependência de idioma/copy.

## PIN

O projeto Android de referência possui `number1` e utiliza o mesmo teclado para criação e confirmação do PIN. Não foi encontrado um locator exclusivo para diferenciar visualmente as duas etapas. A implementação Android usa os IDs `number0` ... `number9` e a transição do próprio fluxo.

Se a build atual expuser um `resource-id` específico para o título de **Criar PIN** e **Confirmar PIN**, pode ser adicionado depois, mas não é obrigatório para a primeira execução.

## Tela de autorização

A tela `AutorizacaoPage` era parte do fluxo iOS. O projeto Android de referência não possui etapa equivalente e o fluxo principal Android não depende dela. O arquivo foi mantido apenas como compatibilidade defensiva.

Só é necessário inspecionar locator de autorização se a build Android atual realmente exibir essa tela depois do PIN.

---

## Locators Android reaproveitados e já mapeados

### Onboarding / Login / PIN

```text
btn_confirmar_informacao
editTextSistema
btn_confirmar
editTextLogin
editTextSenha
number0 ... number9
relative_first_access
```

### Home / Ponto

```text
linearPonto
ponto
menu_esquerdo
bt_init
abrirFecharTotalizador
carregarDadosMenos
carregarDadosMais
```

### Registro sem foto

```text
linear_dialog_geral
relativeDialogPopUp
btnDireito
btnEsquerdo
linearCentroCusto
switchCentroCusto
btn_confirmar
tirarFoto
btn_confirmar_sem_foto
mensagemCamera
textViewRegistroEfetuadoHora
```

### Menu / Ajustes

```text
recyclerviewMenuEsquerdo
menuItemEsquerdoAjuda
menuItemEsquerdoAjustes
menuItemEsquerdoAssinaturaEspelho
menuItemEsquerdoComunicado
menuItemEsquerdoFerias
menuItemEsquerdoHolerite
menuItemEsquerdoInformeRendimento
linearAjustes
```
