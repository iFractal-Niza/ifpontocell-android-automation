/*
 * Ajustes da página nativa do pytest-html, embutidos no report.
 *
 * - Filtros e textos em português: o pytest-html não tem opção de idioma
 *   nem de quais filtros mostrar (os textos vêm fixos do template dele).
 * - Tema Light/Dark (nomes do sistema): seletor com os dois botões no
 *   cabeçalho, o do tema atual destacado; a escolha fica
 *   gravada no navegador (vale para os próximos reports abertos nele).
 * - Textos anexados (árvore da tela, erro resumido) abertos num painel na
 *   própria página, com opção de baixar: abrir data: numa aba nova é
 *   bloqueado pelo navegador.
 * - Imagem ampliada na própria página: o pytest-html abre a imagem numa
 *   aba nova pelo endereço dela. Com a imagem embutida (data:), o
 *   navegador bloqueia e a aba abre em branco.
 */
(function () {
  // Sempre visíveis. Os demais (falha esperada, aprovação inesperada,
  // reexecução) só aparecem quando a execução tiver algum.
  var ROTULOS = {
    failed: 'Falhou',
    passed: 'Passou',
    skipped: 'Pulados',
    error: 'Erros'
  };

  var ROTULOS_EVENTUAIS = {
    xfailed: 'Falhas esperadas',
    xpassed: 'Aprovações inesperadas',
    rerun: 'Reexecuções',
    retried: 'Repetidos'
  };

  // Valores da coluna Status, como nos testes manuais. Só o texto na
  // tela: o pytest-html filtra e ordena pelo valor original, guardado
  // nos dados dele.
  var STATUS = {
    Passed: 'Passou',
    Failed: 'Falhou',
    Skipped: 'Pulado',
    Error: 'Erro',
    XFailed: 'Falha esperada',
    XPassed: 'Aprovação inesperada',
    Rerun: 'Reexecutado'
  };

  function traduzirStatus() {
    document
      .querySelectorAll('#results-table td.col-result')
      .forEach(function (celula) {
        var traducao = STATUS[celula.textContent.trim()];

        if (traducao) {
          celula.textContent = traducao;
        }
      });
  }

  var COLUNAS = {
    Result: 'Status',
    Test: 'Teste',
    Duration: 'Duração',
    Links: 'Evidências'
  };

  function traduzirFiltros() {
    var filtros = document.querySelectorAll(
      '.filters input[data-test-result]'
    );

    filtros.forEach(function (input) {
      var texto = input.nextElementSibling;
      var resultado = input.getAttribute('data-test-result');
      var quantidade = parseInt(texto.textContent, 10) || 0;
      var rotulo = ROTULOS[resultado];

      if (!rotulo) {
        if (quantidade === 0) {
          input.style.display = 'none';
          texto.style.display = 'none';
          return;
        }

        rotulo = ROTULOS_EVENTUAIS[resultado] || resultado;
      }

      texto.textContent = quantidade + ' ' + rotulo;
    });
  }

  function traduzirTextos() {
    var contagem = document.querySelector('.run-count');
    var partes = contagem
      ? /^(\d+) tests? took (.+?)\.?$/.exec(contagem.textContent.trim())
      : null;

    if (partes) {
      contagem.textContent =
        partes[1] +
        (partes[1] === '1' ? ' teste executado em ' : ' testes executados em ') +
        partes[2] +
        '.';
    }

    var dica = document.querySelector('p.filter');

    if (dica) {
      dica.textContent = 'Marque ou desmarque para filtrar os resultados.';
    }

    var mostrar = document.getElementById('show_all_details');
    var ocultar = document.getElementById('hide_all_details');

    if (mostrar) {
      mostrar.textContent = 'Mostrar todos os detalhes';
    }

    if (ocultar) {
      ocultar.textContent = 'Ocultar todos os detalhes';
    }

    var vazio = document.getElementById('template_results-table__body--empty');
    var celula = vazio ? vazio.content.querySelector('td') : null;

    if (celula) {
      celula.textContent = 'Nenhum resultado encontrado. Confira os filtros.';
    }
  }

  function traduzirColunas() {
    document
      .querySelectorAll('#results-table-head th')
      .forEach(function (coluna) {
        var traducao = COLUNAS[coluna.textContent.trim()];

        if (traducao) {
          coluna.textContent = traducao;
        }
      });
  }

  // === Tema Light/Dark ===
  var CHAVE_TEMA = 'qa-report-tema';

  function temaAtual() {
    return document.documentElement.getAttribute('data-theme') === 'dark'
      ? 'dark'
      : 'light';
  }

  function aplicarTema(tema) {
    if (tema === 'dark') {
      document.documentElement.setAttribute('data-theme', 'dark');
    } else {
      document.documentElement.removeAttribute('data-theme');
    }

    document.querySelectorAll('[data-qa-theme]').forEach(function (botao) {
      var ativo = botao.getAttribute('data-qa-theme') === tema;

      botao.setAttribute('aria-pressed', ativo ? 'true' : 'false');
    });
  }

  function prepararBotaoTema() {
    var botoes = document.querySelectorAll('[data-qa-theme]');

    aplicarTema(temaAtual());

    botoes.forEach(function (botao) {
      botao.addEventListener('click', function () {
        var novo = botao.getAttribute('data-qa-theme');

        aplicarTema(novo);

        try {
          localStorage.setItem(CHAVE_TEMA, novo);
        } catch (erro) {
          // Navegador sem armazenamento: o tema vale só nesta aba.
        }
      });
    });
  }

  // === Imagem ampliada ===
  function fecharImagem() {
    var aberta = document.querySelector('.qa-lightbox');

    if (aberta) {
      aberta.remove();
    }
  }

  function abrirImagem(imagem) {
    fecharImagem();

    var legenda = '';
    var midia = imagem.closest('.media');
    var nome = midia ? midia.querySelector('.media__name') : null;

    if (nome) {
      legenda = nome.textContent;
    }

    var fundo = document.createElement('div');
    fundo.className = 'qa-lightbox';
    fundo.title = 'Clique ou tecle Esc para fechar';

    var ampliada = document.createElement('img');
    ampliada.src = imagem.src;
    ampliada.alt = legenda;
    fundo.appendChild(ampliada);

    if (legenda) {
      var texto = document.createElement('div');
      texto.className = 'qa-lightbox-legenda';
      texto.textContent = legenda;
      fundo.appendChild(texto);
    }

    fundo.addEventListener('click', fecharImagem);
    document.body.appendChild(fundo);
  }

  // === Texto anexado ===
  function textoDoDataUri(endereco) {
    var virgula = endereco.indexOf(',');
    var cabecalho = endereco.slice(0, virgula);
    var dados = endereco.slice(virgula + 1);

    if (cabecalho.indexOf(';base64') === -1) {
      return decodeURIComponent(dados);
    }

    var binario = atob(dados);
    var bytes = new Uint8Array(binario.length);

    for (var i = 0; i < binario.length; i += 1) {
      bytes[i] = binario.charCodeAt(i);
    }

    return new TextDecoder('utf-8').decode(bytes);
  }

  function abrirTexto(titulo, endereco) {
    fecharImagem();

    var texto = textoDoDataUri(endereco);
    var fundo = document.createElement('div');
    fundo.className = 'qa-lightbox qa-lightbox--texto';

    var painel = document.createElement('div');
    painel.className = 'qa-texto-painel';

    var cabecalho = document.createElement('div');
    cabecalho.className = 'qa-texto-cabecalho';

    var nome = document.createElement('strong');
    nome.textContent = titulo;
    cabecalho.appendChild(nome);

    var baixar = document.createElement('a');
    var ehXml = texto.trim().indexOf('<?xml') === 0;
    baixar.textContent = 'Baixar';
    baixar.href = URL.createObjectURL(
      new Blob([texto], { type: ehXml ? 'application/xml' : 'text/plain' })
    );
    baixar.download = ehXml ? 'arvore-da-tela.xml' : 'texto.txt';
    cabecalho.appendChild(baixar);

    var fechar = document.createElement('button');
    fechar.type = 'button';
    fechar.textContent = 'Fechar';
    fechar.addEventListener('click', fecharImagem);
    cabecalho.appendChild(fechar);

    var conteudo = document.createElement('pre');
    conteudo.textContent = texto;

    painel.appendChild(cabecalho);
    painel.appendChild(conteudo);
    fundo.appendChild(painel);

    // Clique fora do painel fecha; dentro, não.
    fundo.addEventListener('click', function (evento) {
      if (evento.target === fundo) {
        fecharImagem();
      }
    });

    document.body.appendChild(fundo);
  }

  document.addEventListener(
    'click',
    function (evento) {
      var link = evento.target.closest ? evento.target.closest('a') : null;
      var endereco = link ? link.getAttribute('href') || '' : '';

      if (
        link &&
        link.closest('.col-links') &&
        endereco.indexOf('data:text/') === 0
      ) {
        evento.preventDefault();
        evento.stopPropagation();
        abrirTexto(link.textContent.trim(), endereco);
      }
    },
    true
  );

  // Captura: roda antes do clique do pytest-html (que abriria a aba em
  // branco) e o impede de chegar à imagem.
  document.addEventListener(
    'click',
    function (evento) {
      var imagem = evento.target;

      if (
        imagem.tagName === 'IMG' &&
        imagem.closest('.media-container__viewport')
      ) {
        evento.preventDefault();
        evento.stopPropagation();
        abrirImagem(imagem);
      }
    },
    true
  );

  // Clique em qualquer ponto da linha expande o teste. O pytest-html só
  // escuta as células e pega a linha pelo pai do elemento clicado: no
  // título da coluna Teste (um div dentro da célula) não achava a linha.
  // Repassa o clique à célula de Status, que ele trata. Links e botões
  // seguem normais, e selecionar texto não expande.
  document.addEventListener(
    'click',
    function (evento) {
      var linha = evento.target.closest
        ? evento.target.closest('tr.collapsible')
        : null;
      var status = linha ? linha.querySelector('.col-result') : null;

      if (!status || evento.target === status) {
        return;
      }

      // A lista de classificação não expande a linha (nem deixa o clique
      // chegar ao pytest-html).
      if (evento.target.closest('.qa-classificacao')) {
        evento.stopPropagation();
        return;
      }

      if (
        evento.target.closest('a, button, input, video') ||
        String(window.getSelection ? window.getSelection() : '')
      ) {
        return;
      }

      evento.stopPropagation();
      status.click();
    },
    true
  );

  // === Classificação do erro (Categoria e Tipo) ===
  // Salva no navegador, por arquivo de report e por teste: reabrindo o
  // mesmo arquivo neste navegador, as escolhas voltam. Para enviar a
  // outra pessoa, o botão "Baixar HTML" gera uma cópia com as escolhas
  // gravadas no próprio arquivo (QA_CLASSIFICACAO_FIXA), só leitura.
  var PREFIXO_CLASSIFICACAO = 'qa-classificacao:' + location.pathname + ':';
  var CLASSIFICACAO_FIXA = window.QA_CLASSIFICACAO_FIXA || null;

  // "<nodeid>:<campo>": identifica a lista no armazenamento e na cópia.
  function idClassificacao(lista) {
    return (
      lista.getAttribute('data-teste') + ':' + lista.getAttribute('data-campo')
    );
  }

  function chaveClassificacao(lista) {
    return PREFIXO_CLASSIFICACAO + idClassificacao(lista);
  }

  function lerClassificacao(lista) {
    if (CLASSIFICACAO_FIXA) {
      return CLASSIFICACAO_FIXA[idClassificacao(lista)] || '';
    }

    try {
      return localStorage.getItem(chaveClassificacao(lista)) || '';
    } catch (erro) {
      return '';
    }
  }

  // Na cópia só leitura, a lista vira uma etiqueta com o valor.
  function fixarClassificacao(lista, valor) {
    var etiqueta = document.createElement('span');

    etiqueta.className = 'qa-classificacao qa-classificacao--fixa';
    etiqueta.setAttribute('data-valor', valor);
    etiqueta.textContent = valor || 'Não classificado';
    lista.replaceWith(etiqueta);
  }

  function gravarClassificacao(lista) {
    try {
      if (lista.value) {
        localStorage.setItem(chaveClassificacao(lista), lista.value);
      } else {
        localStorage.removeItem(chaveClassificacao(lista));
      }
    } catch (erro) {
      // Sem armazenamento (ex.: navegação privada): só não salva.
    }
  }

  function marcarClassificacao(lista) {
    lista.setAttribute('data-valor', lista.value);
  }

  // O pytest-html recria as linhas ao ordenar e filtrar: toda lista nova
  // recebe o valor salvo.
  function restaurarClassificacoes() {
    document
      .querySelectorAll(
        'select.qa-classificacao[data-teste]:not([data-restaurada])'
      )
      .forEach(function (lista) {
        var valor = lerClassificacao(lista);

        if (CLASSIFICACAO_FIXA) {
          fixarClassificacao(lista, valor);
          return;
        }

        if (valor) {
          lista.value = valor;
        }

        marcarClassificacao(lista);
        lista.setAttribute('data-restaurada', '');
      });
  }

  document.addEventListener('change', function (evento) {
    var lista = evento.target;

    if (
      lista.classList &&
      lista.classList.contains('qa-classificacao') &&
      lista.hasAttribute('data-teste')
    ) {
      gravarClassificacao(lista);
      marcarClassificacao(lista);
      atualizarCardsManuais();
    }
  });

  // === Baixar HTML com a classificação ===
  // Tudo o que foi escolhido neste report, inclusive em linhas que o
  // filtro escondeu (não estão na página, só no armazenamento).
  function classificacoesEscolhidas() {
    var valores = {};

    try {
      for (var i = 0; i < localStorage.length; i++) {
        var chave = localStorage.key(i);

        if (chave && chave.indexOf(PREFIXO_CLASSIFICACAO) === 0) {
          valores[chave.slice(PREFIXO_CLASSIFICACAO.length)] =
            localStorage.getItem(chave);
        }
      }
    } catch (erro) {
      // Sem armazenamento: fica só o que está na página.
    }

    document
      .querySelectorAll('select.qa-classificacao[data-teste]')
      .forEach(function (lista) {
        if (lista.value) {
          valores[idClassificacao(lista)] = lista.value;
        }
      });

    return valores;
  }

  // JSON seguro dentro da tag script: um "<" no texto vira \u003c, e
  // um fechamento de tag digitado num campo não encerra o script.
  function paraScript(valor) {
    return JSON.stringify(valor).replace(/</g, '\\u003c');
  }

  function nomeDaCopia() {
    var arquivo = decodeURIComponent(
      location.pathname.split('/').pop() || 'report.html'
    );

    return arquivo.replace(/\.html?$/i, '') + '_classificado.html';
  }

  // A página aberta, com as escolhas gravadas. Sai a tabela já montada:
  // o pytest-html remonta tudo ao abrir, a partir dos dados do arquivo,
  // e ela repetiria os prints e o vídeo (o arquivo dobraria de tamanho).
  function htmlDaCopia(manuais, melhoriasFixas) {
    var copia = document.documentElement.cloneNode(true);

    copia
      .querySelectorAll(
        '#results-table > tbody, .qa-lightbox, .qa-bloco-manuais, ' +
          '.qa-bloco-melhorias, .qa-titulo-automatizados'
      )
      .forEach(function (elemento) {
        elemento.remove();
      });

    var fixa = document.createElement('script');
    fixa.textContent =
      'window.QA_CLASSIFICACAO_FIXA = ' +
      paraScript(classificacoesEscolhidas()) +
      ';\nwindow.QA_TESTES_MANUAIS_FIXOS = ' +
      paraScript(manuais) +
      ';\nwindow.QA_MELHORIAS_FIXAS = ' +
      paraScript(melhoriasFixas) +
      ';';

    var cabeca = copia.querySelector('head');
    cabeca.insertBefore(fixa, cabeca.firstChild);

    return '<!DOCTYPE html>\n' + copia.outerHTML;
  }

  // Os arquivos das evidências manuais vêm do IndexedDB e vão embutidos
  // na cópia (por isso a espera).
  function baixarHtml(evento) {
    var botao = evento.currentTarget;
    var texto = botao.textContent;

    botao.disabled = true;
    botao.textContent = 'Preparando...';

    Promise.all([
      comArquivos(testesManuais),
      comArquivos(melhorias),
    ])
      .then(function (listas) {
        baixarArquivo(
          new Blob([htmlDaCopia(listas[0], listas[1])], {
            type: 'text/html;charset=utf-8',
          }),
          nomeDaCopia()
        );
      })
      .catch(function () {
        window.alert(
          'Não foi possível montar a cópia com as evidências manuais.'
        );
      })
      .then(function () {
        botao.disabled = false;
        botao.textContent = texto;
      });
  }

  function baixarArquivo(conteudo, nome) {
    var endereco =
      typeof conteudo === 'string' ? conteudo : URL.createObjectURL(conteudo);
    var link = document.createElement('a');

    link.href = endereco;
    link.download = nome;
    document.body.appendChild(link);
    link.click();
    link.remove();

    if (endereco !== conteudo) {
      setTimeout(function () {
        URL.revokeObjectURL(endereco);
      }, 1000);
    }
  }

  // Na cópia, o botão vira o aviso de que ela é só leitura.
  function prepararBotaoBaixar() {
    document.querySelectorAll('[data-qa-baixar]').forEach(function (botao) {
      if (CLASSIFICACAO_FIXA) {
        var aviso = document.createElement('span');

        aviso.className = 'qa-baixar-html qa-baixar-html--fixo';
        aviso.textContent = 'Somente leitura';
        botao.replaceWith(aviso);
        return;
      }

      botao.addEventListener('click', baixarHtml);
    });
  }

  // === Testes manuais ===
  // Testes feitos fora da automação, acrescentados à mão (botão "+"),
  // num bloco próprio abaixo da tabela dos automatizados, com as mesmas
  // colunas. Salvos no navegador como a classificação; a cópia do
  // "Baixar HTML" os leva gravados, só leitura. Não entram no dashboard
  // nem no PDF.
  //
  // O bloco "Melhorias" (sugestões encontradas nos testes) segue o mesmo
  // modelo e as mesmas colunas (Melhoria no lugar de Teste): implementada,
  // a melhoria também é testada e pode falhar. Começa sem Status.
  var CHAVE_MANUAIS = 'qa-manuais:' + location.pathname;
  var CHAVE_MELHORIAS = 'qa-melhorias:' + location.pathname;
  // Corrigido (retestado, passou) conta como aprovado; Não corrigido (o
  // problema continua), como falha. Os dois também têm card próprio.
  var RESULTADOS_MANUAIS = [
    'Passou',
    'Falhou',
    'Pulado',
    'Corrigido',
    'Não corrigido',
  ];
  var CONTA_DO_STATUS = {
    Passou: 'passed',
    Falhou: 'failed',
    Pulado: 'skipped',
    Corrigido: 'passed',
    'Não corrigido': 'failed',
  };
  var testesManuais = lerLista(CHAVE_MANUAIS, window.QA_TESTES_MANUAIS_FIXOS);
  var melhorias = lerLista(CHAVE_MELHORIAS, window.QA_MELHORIAS_FIXAS).map(
    function (melhoria) {
      // Primeiro formato das melhorias: descricao e prioridade.
      if (melhoria.descricao !== undefined && melhoria.teste === undefined) {
        melhoria.teste = melhoria.descricao;
        delete melhoria.descricao;
        delete melhoria.prioridade;
      }

      return melhoria;
    }
  );

  function lerLista(chave, fixa) {
    if (CLASSIFICACAO_FIXA) {
      return fixa || [];
    }

    try {
      return JSON.parse(localStorage.getItem(chave) || '[]');
    } catch (erro) {
      return [];
    }
  }

  function gravarLista(chave, lista) {
    try {
      if (lista.length) {
        localStorage.setItem(chave, JSON.stringify(lista));
      } else {
        localStorage.removeItem(chave);
      }
    } catch (erro) {
      // Sem armazenamento: as linhas valem só enquanto a página está aberta.
    }
  }

  // Grava as duas listas (testes manuais e melhorias) e atualiza os
  // totais do dashboard.
  function gravarTestesManuais() {
    gravarLista(CHAVE_MANUAIS, testesManuais);
    gravarLista(CHAVE_MELHORIAS, melhorias);
    atualizarTotais();
  }

  // === Totais do dashboard com os testes manuais e as melhorias ===
  // O dashboard vem pronto do Python (utils/report_dashboard.py) só com a
  // automação; os totais dela ficam em data-qa-totais. Aqui entram os
  // testes manuais e as melhorias com Status (sem Status, não contam), e
  // taxa, cards, cor do status e resumo são refeitos com as regras de
  // calcular_taxa_sucesso, _get_status_meta e _build_summary_text. Falha
  // manual não é do smoke: não conta como crítica (só pela taxa).
  // Classes de cor do status (sem etiqueta: CRÍTICO, APROVADO... saíram).
  var CLASSES_STATUS = ['neutral', 'failed', 'unstable', 'caveat', 'healthy'];

  function plural(quantidade, singular, varios) {
    return quantidade === 1 ? singular : varios;
  }

  function formatarTaxa(taxa) {
    var arredondada = Math.round(taxa * 100) / 100;

    return Number.isInteger(arredondada)
      ? arredondada + '%'
      : arredondada.toFixed(2).replace('.', ',') + '%';
  }

  // criticoPelaTaxa: false num fluxo (num fluxo de um teste, uma falha
  // já é 0%), como no build_fluxo_html_card.
  function statusDaExecucao(t, taxa, criticoPelaTaxa) {
    if (t.total === 0 || t.skipped >= t.total) {
      return 'neutral';
    }

    if (t.criticas > 0 || (criticoPelaTaxa !== false && taxa < t.instavel)) {
      return 'failed';
    }

    if (t.failed > 0 || t.error > 0 || taxa < t.saudavel) {
      return 'unstable';
    }

    return t.skipped > 0 ? 'caveat' : 'healthy';
  }

  function resumoDaExecucao(t) {
    if (t.total === 0) {
      return 'Nenhum teste foi executado.';
    }

    if (t.failed === 0 && t.error === 0) {
      return t.skipped
        ? 'Execução concluída sem falhas, com ' +
            t.skipped +
            ' ' +
            plural(t.skipped, 'teste pulado', 'testes pulados') +
            '.'
        : 'Execução concluída sem falhas ou erros técnicos.';
    }

    var problemas = [];

    if (t.failed) {
      problemas.push(
        t.failed +
          ' ' +
          plural(t.failed, 'falha funcional', 'falhas funcionais')
      );
    }

    if (t.error) {
      problemas.push(
        t.error + ' ' + plural(t.error, 'erro técnico', 'erros técnicos')
      );
    }

    // Concordância: "falha" é feminina, "erro" é masculino; os dois
    // juntos ficam no masculino plural.
    var detectado =
      t.failed && t.error
        ? 'detectados'
        : t.failed
          ? plural(t.failed, 'detectada', 'detectadas')
          : plural(t.error, 'detectado', 'detectados');

    var resumo = problemas.join(' e ') + ' ' + detectado + '.';

    if (!t.criticas) {
      return resumo + ' Nenhum teste do smoke falhou.';
    }

    return t.criticas === 1
      ? resumo + ' 1 teste do smoke falhou.'
      : resumo + ' ' + t.criticas + ' testes do smoke falharam.';
  }

  function trocarClasseDeStatus(elemento, status) {
    if (!elemento) {
      return;
    }

    CLASSES_STATUS.forEach(function (classe) {
      elemento.classList.remove(classe);
    });
    elemento.classList.add(status);
  }

  function preencherCard(chave, valor, detalhe, ativo) {
    var card = document.querySelector('[data-qa-kpi="' + chave + '"]');

    if (!card) {
      return;
    }

    card.querySelector('.qa-kpi-value').textContent = valor;

    var texto = card.querySelector('.qa-kpi-detail');
    if (texto && detalhe) {
      texto.textContent = detalhe;
    }

    if (ativo !== undefined) {
      card.classList.toggle('active', ativo);
      card.classList.toggle('muted', !ativo);
    }

    return card;
  }

  function atualizarTotais() {
    var painel = document.querySelector('.qa-dashboard[data-qa-totais]');
    var base;

    try {
      base = JSON.parse(painel.getAttribute('data-qa-totais'));
    } catch (erro) {
      return;
    }

    var t = {};
    Object.keys(base).forEach(function (chave) {
      t[chave] = base[chave];
    });

    var manuais = 0;
    var deMelhorias = 0;

    testesManuais.concat(melhorias).forEach(function (item) {
      var conta = CONTA_DO_STATUS[item.resultado];

      if (!conta) {
        return;
      }

      t[conta] += 1;
      t.total += 1;

      if (melhorias.indexOf(item) === -1) {
        manuais += 1;
      } else {
        deMelhorias += 1;
      }
    });

    var executados = t.passed + t.failed + t.error;
    var taxa = executados
      ? Math.round((t.passed / executados) * 10000) / 100
      : 0;
    var status = statusDaExecucao(t, taxa);
    var partesDoTotal = [];

    if (manuais || deMelhorias) {
      partesDoTotal.push(
        base.total + plural(base.total, ' automatizado', ' automatizados')
      );
      if (manuais) {
        partesDoTotal.push(manuais + plural(manuais, ' manual', ' manuais'));
      }
      if (deMelhorias) {
        partesDoTotal.push(
          deMelhorias + plural(deMelhorias, ' melhoria', ' melhorias')
        );
      }
    }

    trocarClasseDeStatus(
      preencherCard(
        'taxa',
        formatarTaxa(taxa),
        executados
          ? t.passed + ' de ' + executados + ' executados'
          : 'Sem resultados'
      ),
      status
    );
    preencherCard(
      'total',
      t.total,
      partesDoTotal.length ? partesDoTotal.join(' · ') : 'Testes na execução'
    );
    preencherCard('passou', t.passed);
    preencherCard('falhou', t.failed, '', t.failed > 0);
    preencherCard('pulados', t.skipped, '', t.skipped > 0);
    atualizarCardsManuais();

    var alerta = document.querySelector('.qa-execution-alert');
    trocarClasseDeStatus(alerta, status);

    if (alerta) {
      alerta.querySelector('.qa-execution-alert-content strong').textContent =
        resumoDaExecucao(t);
    }

    atualizarFluxos(base);
  }

  // === Cards dos blocos manuais: Corrigido, Não corrigido, Melhorias ===
  // Segunda linha de cards, alinhada à primeira; só aparece com algum
  // teste manual ou melhoria. Mesma estrutura do _build_kpi_card.
  // Melhoria implementada / não implementada contam a coluna Status
  // apont. nas três tabelas (automatizados, manuais e melhorias).
  var CARDS_MANUAIS = [
    ['corrigido', 'passed', 'Corrigido', 'Retestados e aprovados'],
    ['nao-corrigido', 'failed', 'Não corrigido', 'O problema continua'],
    ['melhorias', 'success', 'Qtd melhorias', 'Melhorias registradas'],
    [
      'melhoria-implementada',
      'passed',
      'Melhoria implementada',
      'Status apont.',
    ],
    [
      'melhoria-nao-implementada',
      'failed',
      'Melhoria não implementada',
      'Status apont.',
    ],
  ];

  // Cria a linha (e os cards que faltarem: uma cópia baixada antes pode
  // ter só parte deles).
  function garantirCardsManuais() {
    var linha = document.querySelector('.qa-kpi-grid--manuais');
    var principal = document.querySelector('.qa-kpi-grid');

    if (!linha) {
      if (!principal) {
        return null;
      }

      linha = criar('section', 'qa-kpi-grid qa-kpi-grid--manuais');
      principal.insertAdjacentElement('afterend', linha);
    }

    CARDS_MANUAIS.forEach(function (definicao) {
      if (linha.querySelector('[data-qa-kpi="' + definicao[0] + '"]')) {
        return;
      }

      var card = criar('div', 'qa-kpi-card ' + definicao[1]);

      card.setAttribute('data-qa-kpi', definicao[0]);
      card.appendChild(criar('span', 'qa-kpi-label', definicao[2]));
      card.appendChild(criar('strong', 'qa-kpi-value', '0'));
      card.appendChild(criar('span', 'qa-kpi-detail', definicao[3]));
      linha.appendChild(card);
    });

    return linha;
  }

  // Valores da coluna Status apont. nas três tabelas. Automatizados: o
  // que foi escolhido (ou, na cópia, o que veio gravado nela).
  function apontamentos() {
    var escolhas = CLASSIFICACAO_FIXA || classificacoesEscolhidas();
    var valores = Object.keys(escolhas)
      .filter(function (chave) {
        return /:apontamento$/.test(chave);
      })
      .map(function (chave) {
        return escolhas[chave];
      });

    return valores.concat(
      testesManuais.concat(melhorias).map(function (item) {
        return item.apontamento;
      })
    );
  }

  function atualizarCardsManuais() {
    var linha = garantirCardsManuais();

    if (!linha) {
      return;
    }

    var itens = testesManuais.concat(melhorias);
    var contar = function (status) {
      return itens.filter(function (item) {
        return item.resultado === status;
      }).length;
    };
    var corrigidos = contar('Corrigido');
    var naoCorrigidos = contar('Não corrigido');
    var apontados = apontamentos();
    var contarApontamento = function (valor) {
      return apontados.filter(function (apontado) {
        return apontado === valor;
      }).length;
    };
    var implementadas = contarApontamento('Melhoria implementada');
    var naoImplementadas = contarApontamento('Melhoria não implementada');

    linha.hidden = !itens.length && !implementadas && !naoImplementadas;

    preencherCard('melhoria-implementada', implementadas, '', implementadas > 0);
    preencherCard(
      'melhoria-nao-implementada',
      naoImplementadas,
      '',
      naoImplementadas > 0
    );

    preencherCard('corrigido', corrigidos, '', corrigidos > 0);
    preencherCard('nao-corrigido', naoCorrigidos, '', naoCorrigidos > 0);
    preencherCard(
      'melhorias',
      melhorias.length,
      melhorias.length
        ? plural(melhorias.length, 'Melhoria registrada', 'Melhorias registradas')
        : 'Nenhuma melhoria registrada',
      melhorias.length > 0
    );
  }

  // === Qualidade por fluxo com os testes manuais ===
  // Cada card do Python traz os números do fluxo em data-qa-fluxo. Itens
  // com Status e Fluxo somam no card de mesmo nome (sem diferenciar
  // maiúsculas); nome novo vira um card novo (data-qa-fluxo-manual),
  // refeito a cada mudança.
  function chaveDeFluxo(nome) {
    return String(nome || '').trim().toLowerCase();
  }

  function preencherFluxo(card, base, extra, limites) {
    var n = {
      ok: base.ok + extra.ok,
      fail: base.fail + extra.fail,
      error: base.error,
      skip: base.skip + extra.skip,
    };
    var total = n.ok + n.fail + n.error + n.skip;
    var executados = n.ok + n.fail + n.error;
    var taxa = executados ? Math.round((n.ok / executados) * 10000) / 100 : 0;
    var classe = statusDaExecucao(
      {
        total: total,
        skipped: n.skip,
        failed: n.fail,
        error: n.error,
        criticas: base.critico,
        saudavel: limites.saudavel,
        instavel: limites.instavel,
      },
      taxa,
      false
    );
    var itens = card.querySelectorAll('.qa-flow-meta-item strong');

    card.querySelector('.qa-flow-summary strong').textContent =
      n.ok + '/' + total;
    itens[0].textContent = formatarTaxa(taxa);
    card.querySelector('.qa-flow-meta-item.passed strong').textContent = n.ok;
    card.querySelector('.qa-flow-meta-item.failed strong').textContent =
      n.fail;
    card.querySelector('.qa-flow-meta-item.error strong').textContent =
      n.error;
    card.querySelector('.qa-flow-meta-item.skipped strong').textContent =
      n.skip;

    var barra = card.querySelector('.qa-flow-progress-bar');
    var progresso = card.querySelector('.qa-flow-progress');

    barra.setAttribute('aria-valuenow', taxa);
    progresso.style.width = taxa + '%';
    trocarClasseDeStatus(progresso, classe);
  }

  // Mesma estrutura do build_fluxo_html_card (sem Duração: o teste
  // manual não tem).
  function cardDeFluxo(nome) {
    var card = criar('article', 'qa-flow-row');
    var principal = criar('div', 'qa-flow-main');
    var cabecalho = criar('div', 'qa-flow-heading');
    var resumo = criar('div', 'qa-flow-summary');
    var meta = criar('div', 'qa-flow-meta');
    var barra = criar('div', 'qa-flow-progress-bar');

    cabecalho.appendChild(criar('span', 'qa-flow-title', nome.toUpperCase()));
    resumo.appendChild(criar('strong'));
    resumo.appendChild(criar('span', '', 'testes aprovados'));
    principal.appendChild(cabecalho);
    principal.appendChild(resumo);

    [
      ['', 'Sucesso'],
      ['passed', 'Passou'],
      ['failed', 'Falhou'],
      ['error', 'Execução'],
      ['skipped', 'Pulados'],
    ].forEach(function (item) {
      var bloco = criar('span', ('qa-flow-meta-item ' + item[0]).trim());

      bloco.appendChild(criar('span', '', item[1]));
      bloco.appendChild(criar('strong'));
      meta.appendChild(bloco);
    });

    barra.setAttribute('role', 'progressbar');
    barra.setAttribute('aria-label', 'Taxa de sucesso do fluxo ' + nome);
    barra.setAttribute('aria-valuemin', '0');
    barra.setAttribute('aria-valuemax', '100');
    barra.appendChild(criar('div', 'qa-flow-progress'));

    card.appendChild(principal);
    card.appendChild(meta);
    card.appendChild(barra);
    card.setAttribute('data-qa-fluxo-manual', '');

    return card;
  }

  // Sugestões do campo Fluxo: os fluxos do report e os já digitados.
  function atualizarSugestoesDeFluxo(nomes) {
    var lista = document.getElementById('qa-fluxos-sugeridos');

    if (!lista) {
      lista = criar('datalist');
      lista.id = 'qa-fluxos-sugeridos';
      document.body.appendChild(lista);
    }

    while (lista.firstChild) {
      lista.removeChild(lista.firstChild);
    }

    nomes.forEach(function (nome) {
      lista.appendChild(new Option(nome));
    });
  }

  function atualizarFluxos(limites) {
    var secao = document.querySelector('.qa-fluxos');
    var lista = secao ? secao.querySelector('.qa-flow-list') : null;

    if (!lista) {
      return;
    }

    lista.querySelectorAll('[data-qa-fluxo-manual]').forEach(function (card) {
      card.remove();
    });

    var somas = {};
    var ordem = [];

    testesManuais.concat(melhorias).forEach(function (item) {
      var conta = { passed: 'ok', failed: 'fail', skipped: 'skip' }[
        CONTA_DO_STATUS[item.resultado]
      ];
      var chave = chaveDeFluxo(item.fluxo);

      if (!conta || !chave) {
        return;
      }

      if (!somas[chave]) {
        somas[chave] = { nome: item.fluxo.trim(), ok: 0, fail: 0, skip: 0 };
        ordem.push(chave);
      }

      somas[chave][conta] += 1;
    });

    var nomes = [];
    var vistos = {};

    lista.querySelectorAll('.qa-flow-row[data-qa-fluxo]').forEach(function (
      card
    ) {
      var base;

      try {
        base = JSON.parse(card.getAttribute('data-qa-fluxo'));
      } catch (erro) {
        return;
      }

      var chave = chaveDeFluxo(base.nome);

      preencherFluxo(
        card,
        base,
        somas[chave] || { ok: 0, fail: 0, skip: 0 },
        limites
      );
      nomes.push(base.nome.toUpperCase());
      vistos[chave] = true;
    });

    ordem.forEach(function (chave) {
      if (vistos[chave]) {
        return;
      }

      var card = cardDeFluxo(somas[chave].nome);

      lista.appendChild(card);
      preencherFluxo(
        card,
        { ok: 0, fail: 0, error: 0, skip: 0, critico: 0 },
        somas[chave],
        limites
      );
      nomes.push(somas[chave].nome.toUpperCase());
    });

    testesManuais.concat(melhorias).forEach(function (item) {
      var chave = chaveDeFluxo(item.fluxo);

      if (chave && !vistos[chave] && ordem.indexOf(chave) === -1) {
        ordem.push(chave);
        nomes.push(item.fluxo.trim().toUpperCase());
      }
    });

    atualizarSugestoesDeFluxo(nomes);

    var vazio = secao.querySelector('.qa-empty-state');
    if (vazio) {
      vazio.hidden = lista.children.length > 0;
    }
  }

  // Opções de Categoria e Tipo: vêm no cabeçalho (pytest_report.py).
  function opcoesDaColuna(campo) {
    var coluna = document.querySelector(
      '#results-table-head th[data-campo="' + campo + '"]'
    );

    try {
      return JSON.parse(coluna.getAttribute('data-opcoes')) || [];
    } catch (erro) {
      return [];
    }
  }

  function criar(tag, classe, texto) {
    var elemento = document.createElement(tag);

    if (classe) {
      elemento.className = classe;
    }

    if (texto) {
      elemento.textContent = texto;
    }

    return elemento;
  }

  function campoLista(chave, opcoes, valor, classe, vazio) {
    var lista = criar('select', classe);

    lista.setAttribute('data-chave', chave);

    if (vazio) {
      lista.appendChild(new Option(vazio, ''));
    }

    opcoes.forEach(function (opcao) {
      lista.appendChild(new Option(opcao, opcao));
    });

    lista.value = valor || '';
    lista.setAttribute('data-valor', lista.value);

    return lista;
  }

  function campoTexto(chave, valor, classe, dica) {
    var campo = criar('input', classe);

    campo.type = 'text';
    campo.value = valor || '';
    campo.placeholder = dica;
    campo.setAttribute('data-chave', chave);

    return campo;
  }

  // Fluxo recolhido: só um "+ Fluxo" discreto (ou "Fluxo: X", se já
  // tiver); o clique abre o campo, e sair dele recolhe de novo.
  function textoDoFluxo(fluxo) {
    return fluxo && fluxo.trim() ? 'Fluxo: ' + fluxo.trim() : '+ Fluxo';
  }

  function campoFluxo(valor, origem) {
    var caixa = criar('div', 'qa-fluxo');
    var botao = criar('button', 'qa-fluxo-botao', textoDoFluxo(valor));
    var campo = campoTexto(
      'fluxo',
      valor,
      'qa-manual-campo qa-manual-fluxo',
      'Fluxo (ex.: Jornada E2E)'
    );

    botao.type = 'button';
    botao.title = origem + ': fluxo em Qualidade por fluxo';
    botao.classList.toggle('qa-fluxo-botao--preenchido', !!(valor || '').trim());
    campo.setAttribute('list', 'qa-fluxos-sugeridos');
    campo.setAttribute('data-fluxo-inicial', valor || '');
    campo.hidden = true;

    caixa.appendChild(botao);
    caixa.appendChild(campo);

    return caixa;
  }

  document.addEventListener('click', function (evento) {
    var botao = evento.target.closest('.qa-fluxo-botao');

    if (!botao) {
      return;
    }

    var campo = botao.parentNode.querySelector('.qa-manual-fluxo');

    botao.hidden = true;
    campo.hidden = false;
    campo.focus();
  });

  // Grafia do fluxo: a do card do report (como aparece) ou a do primeiro
  // outro item com o mesmo nome; "teste ricadio" vira "Teste Ricadio".
  function grafiaDoFluxo(nome, item) {
    var chave = chaveDeFluxo(nome);

    if (!chave) {
      return '';
    }

    var cards = document.querySelectorAll('.qa-flow-row[data-qa-fluxo]');

    for (var i = 0; i < cards.length; i += 1) {
      try {
        var base = JSON.parse(cards[i].getAttribute('data-qa-fluxo'));

        if (chaveDeFluxo(base.nome) === chave) {
          return base.nome.toUpperCase();
        }
      } catch (erro) {
        // Card sem dados: segue para o próximo.
      }
    }

    var outro = testesManuais.concat(melhorias).filter(function (outroItem) {
      return outroItem !== item && chaveDeFluxo(outroItem.fluxo) === chave;
    })[0];

    return outro ? outro.fluxo.trim() : nome.trim();
  }

  document.addEventListener('focusout', function (evento) {
    var campo = evento.target;

    if (!campo.classList || !campo.classList.contains('qa-manual-fluxo')) {
      return;
    }

    var item = testeManualDa(campo);
    var anterior = campo.getAttribute('data-fluxo-inicial') || '';

    if (item) {
      item.fluxo = grafiaDoFluxo(campo.value, item);
      campo.value = item.fluxo;
      gravarTestesManuais();
    }

    // Mudou de fluxo: a linha muda de lugar. Redesenha depois que o foco
    // chegou ao próximo campo e o devolve a ele.
    if (item && chaveDeFluxo(item.fluxo) !== chaveDeFluxo(anterior)) {
      setTimeout(redesenharMantendoFoco, 0);
    }

    var botao = campo.parentNode.querySelector('.qa-fluxo-botao');

    botao.textContent = textoDoFluxo(campo.value);
    botao.classList.toggle(
      'qa-fluxo-botao--preenchido',
      !!campo.value.trim()
    );
    botao.hidden = false;
    campo.hidden = true;
  });

  // === Ordem por fluxo nos blocos manuais ===
  // Itens do mesmo fluxo juntos (na ordem em que o fluxo aparece; sem
  // fluxo no fim), com uma borda mais forte na troca de fluxo. Sem
  // título de grupo: o fluxo já está em cada linha e a contagem, em
  // Qualidade por fluxo.
  function desenharGrupos(corpo, lista, colunas, eMelhoria) {
    var ordem = [];
    var porChave = {};

    lista.forEach(function (item) {
      var chave = chaveDeFluxo(item.fluxo);

      if (!porChave[chave]) {
        porChave[chave] = [];
        ordem.push(chave);
      }

      porChave[chave].push(item);
    });

    ordem.sort(function (a, b) {
      return (a ? 0 : 1) - (b ? 0 : 1);
    });

    ordem.forEach(function (chave, posicao) {
      porChave[chave].forEach(function (item, indice) {
        var linha = linhaManual(item, colunas, eMelhoria);

        if (posicao > 0 && indice === 0) {
          linha.classList.add('qa-inicio-de-fluxo');
        }

        corpo.appendChild(linha);
      });
    });
  }

  // Redesenha os blocos e devolve o foco ao campo que o tinha (mesma
  // linha e mesmo campo).
  function redesenharMantendoFoco() {
    var ativo = document.activeElement;
    var linha = ativo && ativo.closest ? ativo.closest('tr.qa-manual-row') : null;
    var id = linha ? linha.getAttribute('data-id') : '';
    var chave = ativo && ativo.getAttribute ? ativo.getAttribute('data-chave') : '';

    redesenharTestesManuais();

    if (id && chave) {
      var alvo = document.querySelector(
        'tr.qa-manual-row[data-id="' + id + '"] [data-chave="' + chave + '"]'
      );

      if (alvo && !alvo.hidden) {
        alvo.focus();
      }
    }
  }

  // Observação do tester: várias linhas.
  function campoObservacao(valor) {
    var campo = criar('textarea', 'qa-manual-campo qa-manual-obs');

    campo.rows = 2;
    campo.value = valor || '';
    campo.placeholder = 'Observação do tester';
    campo.setAttribute('data-chave', 'obs');

    return campo;
  }

  function etiqueta(classe, valor, vazio) {
    var elemento = criar('span', classe, valor || vazio);

    elemento.setAttribute('data-valor', valor || '');

    return elemento;
  }

  // Conteúdo de cada célula, pela coluna do cabeçalho (vale para
  // qualquer ordem de colunas).
  // eMelhoria: linha do bloco Melhorias (Status pode ficar vazio; o
  // campo de texto descreve a melhoria).
  function celulaManual(coluna, teste, eMelhoria) {
    var tipo = coluna.getAttribute('data-column-type');
    var campo = coluna.getAttribute('data-campo');
    var celula = criar('td');
    var fixo = !!CLASSIFICACAO_FIXA;

    if (tipo === 'result') {
      celula.className = 'col-result';
      celula.appendChild(
        fixo
          ? etiqueta('qa-manual-resultado', teste.resultado, '—')
          : campoLista(
              'resultado',
              RESULTADOS_MANUAIS,
              teste.resultado,
              'qa-manual-campo qa-manual-resultado',
              eMelhoria ? 'Selecionar' : ''
            )
      );
    } else if (tipo === 'testId') {
      celula.className = 'col-testId';
      celula.appendChild(
        fixo
          ? criar('div', 'qa-test-title', teste.teste || '—')
          : campoTexto(
              'teste',
              teste.teste,
              'qa-manual-campo qa-manual-teste',
              eMelhoria
                ? 'Descreva a melhoria (tela, comportamento esperado...)'
                : 'CT000 · Descrição do teste'
            )
      );
      var origem = eMelhoria ? 'Melhoria' : 'Teste manual';

      // Fluxo: soma o item no card de mesmo nome em Qualidade por fluxo
      // (ou cria um card novo).
      if (fixo) {
        celula.appendChild(
          criar(
            'div',
            'qa-test-path',
            origem + (teste.fluxo ? ' · Fluxo: ' + teste.fluxo : '')
          )
        );
      } else {
        celula.appendChild(campoFluxo(teste.fluxo, origem));
      }
    } else if (campo) {
      celula.className = 'col-classificacao';
      celula.appendChild(
        fixo
          ? etiqueta(
              'qa-classificacao qa-classificacao--fixa',
              teste[campo],
              'Não classificado'
            )
          : campoLista(
              campo,
              opcoesDaColuna(campo),
              teste[campo],
              'qa-manual-campo qa-classificacao',
              'Selecionar'
            )
      );
    } else if (tipo === 'duration') {
      // Nos blocos manuais, a coluna Duração vira "Obs. Tester".
      celula.className = 'col-obs';
      celula.appendChild(
        fixo
          ? criar('div', 'qa-obs-fixa', teste.obs || '—')
          : campoObservacao(teste.obs)
      );

      // "Ver": a observação inteira numa janela (texto longo fica cortado
      // na célula). Só aparece com texto.
      var ver = criar('button', 'qa-obs-ver', 'Ver');
      ver.type = 'button';
      ver.title = 'Ver a observação inteira';
      ver.hidden = !teste.obs;
      celula.appendChild(ver);
    } else if (coluna === coluna.parentNode.lastElementChild) {
      celula.className = 'col-links';
      celula.appendChild(evidenciasManuais(teste, fixo));
    }

    return celula;
  }

  function linhaManual(teste, colunas, eMelhoria) {
    var linha = criar('tr', 'qa-manual-row');

    linha.setAttribute('data-id', teste.id);
    colunas.forEach(function (coluna) {
      linha.appendChild(celulaManual(coluna, teste, eMelhoria));
    });

    return linha;
  }

  // Cabeçalho da tabela manual: as colunas da tabela dos automatizados,
  // sem a ordenação do pytest-html; Duração vira "Obs. Tester".
  function colunasManuais() {
    return Array.prototype.slice
      .call(document.querySelectorAll('#results-table-head th'))
      .map(function (original) {
        var coluna = criar('th', original.className.replace('sortable', ''));

        coluna.textContent =
          original.getAttribute('data-column-type') === 'duration'
            ? 'Obs. Tester'
            : original.textContent.trim();
        ['data-column-type', 'data-campo'].forEach(function (atributo) {
          if (original.hasAttribute(atributo)) {
            coluna.setAttribute(atributo, original.getAttribute(atributo));
          }
        });

        return coluna;
      });
  }

  function titulo(classe, texto, contagem) {
    var elemento = criar('h3', 'qa-bloco-titulo ' + classe, texto + ' ');

    elemento.appendChild(criar('span', 'qa-bloco-contagem', contagem));

    return elemento;
  }

  function desenharTestesManuais(bloco) {
    var colunas = colunasManuais();
    var linhaDoCabecalho = criar('tr');

    while (bloco.firstChild) {
      bloco.removeChild(bloco.firstChild);
    }

    bloco.appendChild(
      titulo('', 'Testes manuais', '(' + testesManuais.length + ')')
    );

    if (testesManuais.length) {
      var tabela = criar('table', 'qa-manuais-tabela');
      var cabecalho = criar('thead');
      var corpo = criar('tbody', 'qa-manuais');

      colunas.forEach(function (coluna) {
        linhaDoCabecalho.appendChild(coluna);
      });
      cabecalho.appendChild(linhaDoCabecalho);
      tabela.appendChild(cabecalho);

      desenharGrupos(corpo, testesManuais, colunas, false);
      tabela.appendChild(corpo);
      bloco.appendChild(tabela);
    } else {
      bloco.appendChild(
        criar(
          'p',
          'qa-manuais-vazio',
          'Nenhum teste manual. Use o botão abaixo para incluir um.'
        )
      );
    }

    if (!CLASSIFICACAO_FIXA) {
      var acoes = criar('div', 'qa-manuais-acoes');
      var adicionar = criar(
        'button',
        'qa-adicionar-teste',
        '+ Adicionar teste manual'
      );

      adicionar.type = 'button';
      acoes.appendChild(adicionar);
      bloco.appendChild(acoes);
    }
  }

  // Título dos automatizados antes da tabela do pytest-html e o bloco
  // dos manuais depois. Ficam fora da tabela: sobrevivem quando ela é
  // recriada. Na cópia sem testes manuais, o bloco não aparece.
  function garantirTestesManuais() {
    var tabela = document.getElementById('results-table');

    if (!tabela || !tabela.querySelector('#results-table-head th')) {
      return;
    }

    if (!document.querySelector('.qa-titulo-automatizados')) {
      tabela.insertAdjacentElement(
        'beforebegin',
        titulo('qa-titulo-automatizados', 'Testes automatizados', '')
      );
      atualizarContagemAutomatizados();
    }

    var manuais = document.querySelector('.qa-bloco-manuais');

    if (!manuais && !(CLASSIFICACAO_FIXA && !testesManuais.length)) {
      manuais = criar('section', 'qa-bloco-manuais');

      desenharTestesManuais(manuais);
      tabela.insertAdjacentElement('afterend', manuais);
    }

    if (
      !document.querySelector('.qa-bloco-melhorias') &&
      !(CLASSIFICACAO_FIXA && !melhorias.length)
    ) {
      var blocoMelhorias = criar('section', 'qa-bloco-melhorias');

      desenharMelhorias(blocoMelhorias);
      (manuais || tabela).insertAdjacentElement('afterend', blocoMelhorias);
    }
  }

  // === Melhorias ===
  function desenharMelhorias(bloco) {
    while (bloco.firstChild) {
      bloco.removeChild(bloco.firstChild);
    }

    bloco.appendChild(titulo('', 'Melhorias', '(' + melhorias.length + ')'));

    if (melhorias.length) {
      var tabela = criar('table', 'qa-manuais-tabela qa-melhorias-tabela');
      var cabecalho = criar('thead');
      var linhaDoCabecalho = criar('tr');
      var corpo = criar('tbody');
      var colunas = colunasManuais();

      colunas.forEach(function (coluna) {
        if (coluna.getAttribute('data-column-type') === 'testId') {
          coluna.textContent = 'Melhoria';
        }

        linhaDoCabecalho.appendChild(coluna);
      });
      cabecalho.appendChild(linhaDoCabecalho);
      tabela.appendChild(cabecalho);

      desenharGrupos(corpo, melhorias, colunas, true);
      tabela.appendChild(corpo);
      bloco.appendChild(tabela);
    } else {
      bloco.appendChild(
        criar(
          'p',
          'qa-manuais-vazio',
          'Nenhuma melhoria. Use o botão abaixo para incluir uma.'
        )
      );
    }

    if (!CLASSIFICACAO_FIXA) {
      var acoes = criar('div', 'qa-manuais-acoes');
      var adicionar = criar(
        'button',
        'qa-adicionar-teste qa-adicionar-melhoria',
        '+ Adicionar melhoria'
      );

      adicionar.type = 'button';
      acoes.appendChild(adicionar);
      bloco.appendChild(acoes);
    }
  }

  // Total da execução (do pytest-html), não o que o filtro mostra.
  function atualizarContagemAutomatizados() {
    var contagem = document.querySelector(
      '.qa-titulo-automatizados .qa-bloco-contagem'
    );
    var total = 0;

    // O número fica no span logo após cada filtro; rerun é repetição,
    // não teste.
    document
      .querySelectorAll('.filters [data-test-result]')
      .forEach(function (filtro) {
        var rotulo = filtro.nextElementSibling;
        var numero = rotulo ? parseInt(rotulo.textContent, 10) : 0;

        if (filtro.getAttribute('data-test-result') !== 'rerun') {
          total += isNaN(numero) ? 0 : numero;
        }
      });

    if (contagem && total) {
      contagem.textContent = '(' + total + ')';
    }
  }

  // O item (teste manual ou melhoria) da linha onde está o elemento.
  function testeManualDa(elemento) {
    var linha = elemento.closest ? elemento.closest('tr.qa-manual-row') : null;
    var id = linha ? linha.getAttribute('data-id') : null;

    return testesManuais.concat(melhorias).filter(function (item) {
      return item.id === id;
    })[0];
  }

  function redesenharTestesManuais() {
    var bloco = document.querySelector('.qa-bloco-manuais');
    var blocoMelhorias = document.querySelector('.qa-bloco-melhorias');

    if (bloco) {
      desenharTestesManuais(bloco);
    }

    if (blocoMelhorias) {
      desenharMelhorias(blocoMelhorias);
    }
  }

  function focarUltimo(seletor) {
    var campos = document.querySelectorAll(seletor);

    if (campos.length) {
      campos[campos.length - 1].focus();
    }
  }

  document.addEventListener('click', function (evento) {
    if (evento.target.closest('.qa-adicionar-melhoria')) {
      melhorias.push({
        id: 'r' + Date.now(),
        resultado: '',
        teste: '',
        categoria: '',
        tipo: '',
        obs: '',
        fluxo: '',
      });
      gravarTestesManuais();
      redesenharTestesManuais();
      focarUltimo('.qa-melhorias-tabela .qa-manual-teste');
      return;
    }

    if (evento.target.closest('.qa-adicionar-teste')) {
      testesManuais.push({
        id: 'm' + Date.now(),
        resultado: 'Falhou',
        teste: '',
        categoria: '',
        tipo: '',
        obs: '',
        fluxo: '',
      });
      gravarTestesManuais();
      redesenharTestesManuais();
      focarUltimo('.qa-bloco-manuais .qa-manual-teste');
      return;
    }

    var remover = evento.target.closest('.qa-manual-remover');
    var teste = remover ? testeManualDa(remover) : null;
    var eMelhoria = melhorias.indexOf(teste) !== -1;

    if (
      teste &&
      window.confirm(
        eMelhoria ? 'Remover esta melhoria?' : 'Remover este teste manual?'
      )
    ) {
      (teste.evidencias || []).forEach(function (evidencia) {
        apagarArquivo(evidencia.id);
      });
      testesManuais = testesManuais.filter(function (outro) {
        return outro !== teste;
      });
      melhorias = melhorias.filter(function (outra) {
        return outra !== teste;
      });
      gravarTestesManuais();
      redesenharTestesManuais();
      return;
    }

    var verObs = evento.target.closest('.qa-obs-ver');
    var comObs = verObs ? testeManualDa(verObs) : null;

    if (comObs) {
      abrirTexto(
        'Obs. Tester' + (comObs.teste ? ' · ' + comObs.teste : ''),
        'data:text/plain;charset=utf-8,' + encodeURIComponent(comObs.obs || '')
      );
      return;
    }

    var anexar = evento.target.closest('.qa-evidencia-anexar');

    if (anexar) {
      escolherArquivos(testeManualDa(anexar));
      return;
    }

    var abrir = evento.target.closest('.qa-evidencia-abrir');

    if (abrir) {
      abrirEvidenciaManual(
        testeManualDa(abrir),
        abrir.getAttribute('data-evidencia')
      );
      return;
    }

    var tirar = evento.target.closest('.qa-evidencia-tirar');
    var dono = tirar ? testeManualDa(tirar) : null;

    if (dono && window.confirm('Remover esta evidência?')) {
      var id = tirar.getAttribute('data-evidencia');

      apagarArquivo(id);
      dono.evidencias = (dono.evidencias || []).filter(function (evidencia) {
        return evidencia.id !== id;
      });
      gravarTestesManuais();
      redesenharTestesManuais();
    }
  });

  // === Evidências dos testes manuais ===
  // O arquivo (imagem, vídeo, PDF...) fica no IndexedDB do navegador: o
  // localStorage só comporta alguns MB. No teste, só id, nome e tipo. Na
  // cópia do "Baixar HTML", o arquivo vai embutido (campo dados).
  var LIMITE_EVIDENCIA_MB = 50;
  var bancoDeArquivos = null;

  function abrirBanco() {
    if (!bancoDeArquivos) {
      bancoDeArquivos = new Promise(function (resolver, rejeitar) {
        var pedido = indexedDB.open('qa-report-evidencias', 1);

        pedido.onupgradeneeded = function () {
          pedido.result.createObjectStore('arquivos');
        };
        pedido.onsuccess = function () {
          resolver(pedido.result);
        };
        pedido.onerror = function () {
          rejeitar(pedido.error);
        };
      });
    }

    return bancoDeArquivos;
  }

  function operarArquivo(modo, operacao) {
    return abrirBanco().then(function (banco) {
      return new Promise(function (resolver, rejeitar) {
        var pedido = operacao(
          banco.transaction('arquivos', modo).objectStore('arquivos')
        );

        pedido.onsuccess = function () {
          resolver(pedido.result);
        };
        pedido.onerror = function () {
          rejeitar(pedido.error);
        };
      });
    });
  }

  function guardarArquivo(id, dados) {
    return operarArquivo('readwrite', function (arquivos) {
      return arquivos.put(dados, id);
    });
  }

  function lerArquivo(id) {
    return operarArquivo('readonly', function (arquivos) {
      return arquivos.get(id);
    });
  }

  function apagarArquivo(id) {
    operarArquivo('readwrite', function (arquivos) {
      return arquivos.delete(id);
    }).catch(function () {
      // Sem banco: não há o que apagar.
    });
  }

  function dadosDaEvidencia(evidencia) {
    return evidencia.dados
      ? Promise.resolve(evidencia.dados)
      : lerArquivo(evidencia.id);
  }

  // A lista (testes manuais ou melhorias) com os arquivos embutidos.
  function comArquivos(lista) {
    return Promise.all(
      lista.map(function (teste) {
        return Promise.all(
          (teste.evidencias || []).map(function (evidencia) {
            return dadosDaEvidencia(evidencia).then(function (dados) {
              return {
                id: evidencia.id,
                nome: evidencia.nome,
                tipo: evidencia.tipo,
                dados: dados || '',
              };
            });
          })
        ).then(function (evidencias) {
          var copia = {};

          Object.keys(teste).forEach(function (chave) {
            copia[chave] = teste[chave];
          });
          copia.evidencias = evidencias;

          return copia;
        });
      })
    );
  }

  function lerComoDataUrl(arquivo) {
    return new Promise(function (resolver, rejeitar) {
      var leitor = new FileReader();

      leitor.onload = function () {
        resolver(leitor.result);
      };
      leitor.onerror = function () {
        rejeitar(leitor.error);
      };
      leitor.readAsDataURL(arquivo);
    });
  }

  // === Compressão das evidências manuais ===
  // Feita no navegador, ao anexar: a cópia do "Baixar HTML" embute os
  // arquivos, e um print ou vídeo do celular em resolução cheia pesa
  // muito. Se o resultado não ficar menor, vai o original.
  var IMAGEM_MAXIMA = { largura: 1280, altura: 1600 };
  var QUALIDADE_JPEG = 0.8;
  var VIDEO_LARGURA_MAXIMA = 720;
  var VIDEO_BITS_POR_SEGUNDO = 1500000;
  var AUDIO_BITS_POR_SEGUNDO = 96000;

  function trocarExtensao(nome, extensao) {
    return nome.replace(/\.[^.]*$/, '') + '.' + extensao;
  }

  // Imagem: cabe em 1280x1600, em JPEG 80% (fundo branco para PNG com
  // transparência). GIF e SVG ficam como estão.
  function comprimirImagem(arquivo) {
    if (!/^image\/(png|jpeg|webp|bmp)$/.test(arquivo.type)) {
      return Promise.resolve(null);
    }

    return new Promise(function (resolver) {
      var endereco = URL.createObjectURL(arquivo);
      var imagem = new Image();

      imagem.onload = function () {
        var escala = Math.min(
          1,
          IMAGEM_MAXIMA.largura / imagem.naturalWidth,
          IMAGEM_MAXIMA.altura / imagem.naturalHeight
        );
        var tela = document.createElement('canvas');

        tela.width = Math.round(imagem.naturalWidth * escala);
        tela.height = Math.round(imagem.naturalHeight * escala);

        var pincel = tela.getContext('2d');
        pincel.fillStyle = '#ffffff';
        pincel.fillRect(0, 0, tela.width, tela.height);
        pincel.drawImage(imagem, 0, 0, tela.width, tela.height);
        URL.revokeObjectURL(endereco);

        tela.toBlob(
          function (comprimida) {
            resolver(
              comprimida
                ? {
                    conteudo: comprimida,
                    nome: trocarExtensao(arquivo.name, 'jpg'),
                  }
                : null
            );
          },
          'image/jpeg',
          QUALIDADE_JPEG
        );
      };
      imagem.onerror = function () {
        URL.revokeObjectURL(endereco);
        resolver(null);
      };
      imagem.src = endereco;
    });
  }

  // Formato com vídeo e áudio: mp4 (H.264 + AAC) quando o navegador
  // grava mp4, senão webm (VP9 + Opus).
  function formatoDeVideo() {
    if (
      !window.MediaRecorder ||
      !HTMLCanvasElement.prototype.captureStream ||
      !(window.AudioContext || window.webkitAudioContext)
    ) {
      return '';
    }

    return (
      [
        'video/mp4;codecs=avc1,mp4a.40.2',
        'video/mp4',
        'video/webm;codecs=vp9,opus',
        'video/webm',
      ].filter(function (formato) {
        return MediaRecorder.isTypeSupported(formato);
      })[0] || ''
    );
  }

  // Vídeo: regravado no navegador em 720 px de largura, com o áudio. O
  // navegador só regrava tocando o vídeo: demora a duração dele. A imagem
  // é desenhada quadro a quadro num canvas; o áudio vai do vídeo para a
  // gravação pela Web Audio API, sem sair no alto-falante. Se o navegador
  // não deixar tocar com som (o Safari exige um clique recente), fica o
  // original, para não perder o áudio.
  function comprimirVideo(arquivo, aoProgredir) {
    var formato = formatoDeVideo();

    if (!formato) {
      return Promise.resolve(null);
    }

    return new Promise(function (resolver) {
      var endereco = URL.createObjectURL(arquivo);
      var video = document.createElement('video');
      var partes = [];
      var terminou = false;

      var audio = null;

      function concluir(resultado) {
        if (!terminou) {
          terminou = true;
          URL.revokeObjectURL(endereco);

          if (audio) {
            audio.close();
          }

          resolver(resultado);
        }
      }

      // Com som: o áudio é desviado para a gravação (não toca).
      video.muted = false;
      video.playsInline = true;
      video.preload = 'auto';

      video.onerror = function () {
        concluir(null);
      };

      video.onloadedmetadata = function () {
        var escala = Math.min(1, VIDEO_LARGURA_MAXIMA / video.videoWidth);
        var tela = document.createElement('canvas');

        // Dimensões pares: exigência dos codificadores de vídeo.
        tela.width = Math.max(2, Math.round((video.videoWidth * escala) / 2) * 2);
        tela.height = Math.max(
          2,
          Math.round((video.videoHeight * escala) / 2) * 2
        );

        var pincel = tela.getContext('2d');
        var gravador;

        try {
          var Contexto = window.AudioContext || window.webkitAudioContext;

          audio = new Contexto();

          var saidaDeAudio = audio.createMediaStreamDestination();
          audio.createMediaElementSource(video).connect(saidaDeAudio);

          gravador = new MediaRecorder(
            new MediaStream(
              tela
                .captureStream(30)
                .getVideoTracks()
                .concat(saidaDeAudio.stream.getAudioTracks())
            ),
            {
              mimeType: formato,
              videoBitsPerSecond: VIDEO_BITS_POR_SEGUNDO,
              audioBitsPerSecond: AUDIO_BITS_POR_SEGUNDO,
            }
          );
        } catch (erro) {
          concluir(null);
          return;
        }

        gravador.ondataavailable = function (evento) {
          if (evento.data && evento.data.size) {
            partes.push(evento.data);
          }
        };
        gravador.onstop = function () {
          var tipo = formato.split(';')[0];

          concluir({
            conteudo: new Blob(partes, { type: tipo }),
            nome: trocarExtensao(
              arquivo.name,
              tipo === 'video/mp4' ? 'mp4' : 'webm'
            ),
          });
        };

        function desenhar() {
          pincel.drawImage(video, 0, 0, tela.width, tela.height);

          if (video.duration && isFinite(video.duration)) {
            aoProgredir(Math.min(1, video.currentTime / video.duration));
          }

          if (!video.ended && !video.paused) {
            agendar();
          }
        }

        function agendar() {
          if (video.requestVideoFrameCallback) {
            video.requestVideoFrameCallback(desenhar);
          } else {
            requestAnimationFrame(desenhar);
          }
        }

        video.onended = function () {
          desenhar();
          gravador.stop();
        };

        gravador.start(1000);
        audio
          .resume()
          .then(function () {
            return video.play();
          })
          .then(agendar)
          .catch(function () {
            gravador.onstop = null;
            gravador.stop();
            concluir(null);
          });
      };

      video.src = endereco;
    });
  }

  // O arquivo a guardar: o comprimido, se ficou menor.
  function versaoMenor(arquivo, aoProgredir) {
    var compressao = /^video\//.test(arquivo.type)
      ? comprimirVideo(arquivo, aoProgredir)
      : comprimirImagem(arquivo);

    return compressao
      .catch(function () {
        return null;
      })
      .then(function (comprimido) {
        if (comprimido && comprimido.conteudo.size < arquivo.size) {
          return comprimido;
        }

        return { conteudo: arquivo, nome: arquivo.name };
      });
  }

  // Mostra o andamento no botão de anexar da linha.
  function avisarAnexo(teste, texto) {
    var botao = document.querySelector(
      'tr.qa-manual-row[data-id="' + teste.id + '"] .qa-evidencia-anexar'
    );

    if (botao) {
      botao.disabled = true;
      botao.textContent = texto;
    }
  }

  // Um arquivo de cada vez (vídeo regravado em paralelo disputaria a
  // reprodução); cada um entra no teste assim que fica pronto.
  function anexarArquivos(teste, arquivos) {
    var limite = LIMITE_EVIDENCIA_MB * 1024 * 1024;
    var deFora = [];
    var fila = Promise.resolve();

    arquivos.forEach(function (arquivo, indice) {
      fila = fila.then(function () {
        var posicao =
          arquivos.length > 1 ? ' (' + (indice + 1) + '/' + arquivos.length + ')' : '';

        avisarAnexo(teste, 'Comprimindo' + posicao + '...');

        return versaoMenor(arquivo, function (fracao) {
          avisarAnexo(
            teste,
            'Comprimindo vídeo' + posicao + ' ' + Math.round(fracao * 100) + '%'
          );
        }).then(function (final) {
          if (final.conteudo.size > limite) {
            deFora.push(arquivo.name);
            return;
          }

          var id = 'e' + Date.now() + '-' + indice;

          return lerComoDataUrl(final.conteudo)
            .then(function (dados) {
              return guardarArquivo(id, dados);
            })
            .then(function () {
              teste.evidencias = (teste.evidencias || []).concat({
                id: id,
                nome: final.nome,
                tipo: final.conteudo.type || arquivo.type,
              });
              gravarTestesManuais();
            });
        });
      });
    });

    fila
      .catch(function () {
        window.alert(
          'Não foi possível guardar o arquivo neste navegador ' +
            '(sem espaço ou navegação privada).'
        );
      })
      .then(function () {
        redesenharTestesManuais();

        if (deFora.length) {
          window.alert(
            'Ficaram de fora (acima de ' +
              LIMITE_EVIDENCIA_MB +
              ' MB mesmo comprimidos): ' +
              deFora.join(', ')
          );
        }
      });
  }

  // Vários arquivos de uma vez.
  function escolherArquivos(teste) {
    if (!teste) {
      return;
    }

    var seletor = document.createElement('input');

    seletor.type = 'file';
    seletor.multiple = true;
    seletor.accept = 'image/*,video/*,application/pdf';
    seletor.addEventListener('change', function () {
      anexarArquivos(teste, Array.prototype.slice.call(seletor.files));
    });
    seletor.click();
  }

  // Imagem e vídeo abrem ampliados na página; o resto é baixado.
  function abrirEvidenciaManual(teste, id) {
    var evidencia = ((teste && teste.evidencias) || []).filter(function (e) {
      return e.id === id;
    })[0];

    if (!evidencia) {
      return;
    }

    dadosDaEvidencia(evidencia).then(function (dados) {
      if (!dados) {
        window.alert('Arquivo não encontrado neste navegador.');
        return;
      }

      var tipo = evidencia.tipo || '';

      if (tipo.indexOf('image/') !== 0 && tipo.indexOf('video/') !== 0) {
        baixarArquivo(dados, evidencia.nome);
        return;
      }

      fecharImagem();

      var fundo = criar('div', 'qa-lightbox');
      var midia = criar(tipo.indexOf('video/') === 0 ? 'video' : 'img');

      fundo.title = 'Clique fora ou tecle Esc para fechar';
      midia.src = dados;

      if (midia.tagName === 'VIDEO') {
        midia.controls = true;
        midia.autoplay = true;
      } else {
        midia.alt = evidencia.nome;
      }

      fundo.appendChild(midia);
      fundo.appendChild(criar('div', 'qa-lightbox-legenda', evidencia.nome));
      fundo.addEventListener('click', function (clique) {
        if (clique.target === fundo) {
          fecharImagem();
        }
      });
      document.body.appendChild(fundo);
    });
  }

  var ICONE_LIXEIRA =
    '<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true" ' +
    'fill="none" stroke="currentColor" stroke-width="2" ' +
    'stroke-linecap="round" stroke-linejoin="round">' +
    '<path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6M10 11v6M14 11v6"/></svg>';

  // Célula Evidências da linha manual: as evidências anexadas, o botão de
  // anexar e, na ponta direita, a lixeira da linha (teste ou melhoria).
  function evidenciasManuais(teste, fixo) {
    var caixa = criar('div', 'qa-manual-evidencias');
    var lista = criar('div', 'qa-evidencias-lista');

    (teste.evidencias || []).forEach(function (evidencia) {
      var item = criar('span', 'qa-evidencia-manual');
      var abrir = criar('button', 'col-links__extra qa-evidencia-abrir');

      abrir.type = 'button';
      abrir.textContent = evidencia.nome;
      abrir.title = evidencia.nome;
      abrir.setAttribute('data-evidencia', evidencia.id);
      item.appendChild(abrir);

      if (!fixo) {
        var tirar = criar('button', 'qa-evidencia-tirar', '×');

        tirar.type = 'button';
        tirar.title = 'Remover evidência';
        tirar.setAttribute('data-evidencia', evidencia.id);
        item.appendChild(tirar);
      }

      lista.appendChild(item);
    });

    if (!fixo) {
      var anexar = criar('button', 'qa-evidencia-anexar', '+ Anexar');

      anexar.type = 'button';
      anexar.title = 'Imagens, vídeos ou PDF (pode escolher vários)';
      lista.appendChild(anexar);
    }

    caixa.appendChild(lista);

    if (!fixo) {
      var lixeira = criar('button', 'qa-manual-remover');

      lixeira.type = 'button';
      lixeira.title = 'Remover linha';
      lixeira.setAttribute('aria-label', 'Remover linha');
      lixeira.innerHTML = ICONE_LIXEIRA;
      caixa.appendChild(lixeira);
    } else if (!(teste.evidencias || []).length) {
      caixa.appendChild(criar('span', 'qa-sem-erro', '—'));
    }

    return caixa;
  }

  function atualizarTesteManual(evento) {
    var campo = evento.target;
    var chave = campo.getAttribute && campo.getAttribute('data-chave');
    var teste = chave ? testeManualDa(campo) : null;

    if (!teste) {
      return;
    }

    teste[chave] = campo.value;
    campo.setAttribute('data-valor', campo.value);

    if (chave === 'obs') {
      var ver = campo.parentNode.querySelector('.qa-obs-ver');
      if (ver) {
        ver.hidden = !campo.value.trim();
      }
    }

    gravarTestesManuais();
  }

  document.addEventListener('input', atualizarTesteManual);
  document.addEventListener('change', atualizarTesteManual);

  function aoMudarAPagina() {
    traduzirStatus();
    restaurarClassificacoes();
    garantirTestesManuais();
  }

  if (window.MutationObserver) {
    new MutationObserver(aoMudarAPagina).observe(
      document.documentElement,
      { childList: true, subtree: true }
    );
  }

  document.addEventListener('keydown', function (evento) {
    if (evento.key === 'Escape') {
      fecharImagem();
    }
  });

  function traduzir() {
    traduzirFiltros();
    traduzirTextos();
    traduzirColunas();
    prepararBotaoTema();
    prepararBotaoBaixar();
    aoMudarAPagina();
    atualizarTotais();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', traduzir);
  } else {
    traduzir();
  }
})();
