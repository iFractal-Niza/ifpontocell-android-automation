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

  var COLUNAS = {
    Result: 'Resultado',
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
  function htmlDaCopia(manuaisComArquivos) {
    var copia = document.documentElement.cloneNode(true);

    copia
      .querySelectorAll(
        '#results-table > tbody, .qa-lightbox, .qa-bloco-manuais, ' +
          '.qa-titulo-automatizados'
      )
      .forEach(function (elemento) {
        elemento.remove();
      });

    var fixa = document.createElement('script');
    fixa.textContent =
      'window.QA_CLASSIFICACAO_FIXA = ' +
      paraScript(classificacoesEscolhidas()) +
      ';\nwindow.QA_TESTES_MANUAIS_FIXOS = ' +
      paraScript(manuaisComArquivos) +
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

    manuaisComArquivos()
      .then(function (manuais) {
        baixarArquivo(
          new Blob([htmlDaCopia(manuais)], {
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
  var CHAVE_MANUAIS = 'qa-manuais:' + location.pathname;
  var RESULTADOS_MANUAIS = ['Passou', 'Falhou', 'Pulado'];
  var testesManuais = lerTestesManuais();

  function lerTestesManuais() {
    if (CLASSIFICACAO_FIXA) {
      return window.QA_TESTES_MANUAIS_FIXOS || [];
    }

    try {
      return JSON.parse(localStorage.getItem(CHAVE_MANUAIS) || '[]');
    } catch (erro) {
      return [];
    }
  }

  function gravarTestesManuais() {
    try {
      if (testesManuais.length) {
        localStorage.setItem(CHAVE_MANUAIS, JSON.stringify(testesManuais));
      } else {
        localStorage.removeItem(CHAVE_MANUAIS);
      }
    } catch (erro) {
      // Sem armazenamento: as linhas valem só enquanto a página está aberta.
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

  function etiqueta(classe, valor, vazio) {
    var elemento = criar('span', classe, valor || vazio);

    elemento.setAttribute('data-valor', valor || '');

    return elemento;
  }

  // Conteúdo de cada célula, pela coluna do cabeçalho (vale para
  // qualquer ordem de colunas).
  function celulaManual(coluna, teste) {
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
              'qa-manual-campo qa-manual-resultado'
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
              'CT000 · Descrição do teste'
            )
      );
      celula.appendChild(criar('div', 'qa-test-path', 'Teste manual'));
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
      celula.className = 'col-duration';
      celula.appendChild(
        fixo
          ? document.createTextNode(teste.duracao || '—')
          : campoTexto(
              'duracao',
              teste.duracao,
              'qa-manual-campo qa-manual-duracao',
              '00:00:00'
            )
      );
    } else if (coluna === coluna.parentNode.lastElementChild) {
      celula.className = 'col-links';
      celula.appendChild(evidenciasManuais(teste, fixo));
    }

    return celula;
  }

  function linhaManual(teste, colunas) {
    var linha = criar('tr', 'qa-manual-row');

    linha.setAttribute('data-id', teste.id);
    colunas.forEach(function (coluna) {
      linha.appendChild(celulaManual(coluna, teste));
    });

    return linha;
  }

  // Cabeçalho da tabela manual: as colunas da tabela dos automatizados,
  // sem a ordenação do pytest-html.
  function colunasManuais() {
    return Array.prototype.slice
      .call(document.querySelectorAll('#results-table-head th'))
      .map(function (original) {
        var coluna = criar('th', original.className.replace('sortable', ''));

        coluna.textContent = original.textContent.trim();
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

      testesManuais.forEach(function (teste) {
        corpo.appendChild(linhaManual(teste, colunas));
      });
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

    if (
      !document.querySelector('.qa-bloco-manuais') &&
      !(CLASSIFICACAO_FIXA && !testesManuais.length)
    ) {
      var bloco = criar('section', 'qa-bloco-manuais');

      desenharTestesManuais(bloco);
      tabela.insertAdjacentElement('afterend', bloco);
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

  function testeManualDa(elemento) {
    var linha = elemento.closest ? elemento.closest('tr.qa-manual-row') : null;
    var id = linha ? linha.getAttribute('data-id') : null;

    return testesManuais.filter(function (teste) {
      return teste.id === id;
    })[0];
  }

  function redesenharTestesManuais() {
    var bloco = document.querySelector('.qa-bloco-manuais');

    if (bloco) {
      desenharTestesManuais(bloco);
    }
  }

  document.addEventListener('click', function (evento) {
    if (evento.target.closest('.qa-adicionar-teste')) {
      testesManuais.push({
        id: 'm' + Date.now(),
        resultado: 'Falhou',
        teste: '',
        categoria: '',
        tipo: '',
        duracao: '',
      });
      gravarTestesManuais();
      redesenharTestesManuais();

      var campos = document.querySelectorAll('.qa-manual-teste');
      if (campos.length) {
        campos[campos.length - 1].focus();
      }
      return;
    }

    var remover = evento.target.closest('.qa-manual-remover');
    var teste = remover ? testeManualDa(remover) : null;

    if (teste && window.confirm('Remover este teste manual?')) {
      (teste.evidencias || []).forEach(function (evidencia) {
        apagarArquivo(evidencia.id);
      });
      testesManuais = testesManuais.filter(function (outro) {
        return outro !== teste;
      });
      gravarTestesManuais();
      redesenharTestesManuais();
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

  function manuaisComArquivos() {
    return Promise.all(
      testesManuais.map(function (teste) {
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

  function formatoDeVideo() {
    if (
      !window.MediaRecorder ||
      !HTMLCanvasElement.prototype.captureStream
    ) {
      return '';
    }

    return (
      [
        'video/mp4;codecs=avc1',
        'video/mp4',
        'video/webm;codecs=vp9',
        'video/webm',
      ].filter(function (formato) {
        return MediaRecorder.isTypeSupported(formato);
      })[0] || ''
    );
  }

  // Vídeo: regravado no navegador em 720 px de largura, sem áudio (mp4
  // quando o navegador grava mp4, senão webm). O navegador só regrava
  // tocando o vídeo: demora a duração dele.
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

      function concluir(resultado) {
        if (!terminou) {
          terminou = true;
          URL.revokeObjectURL(endereco);
          resolver(resultado);
        }
      }

      video.muted = true;
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
          gravador = new MediaRecorder(tela.captureStream(30), {
            mimeType: formato,
            videoBitsPerSecond: VIDEO_BITS_POR_SEGUNDO,
          });
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
        video
          .play()
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
  // anexar e, na ponta direita, a lixeira do teste.
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
      var anexar = criar(
        'button',
        'qa-evidencia-anexar',
        '+ Anexar evidências'
      );

      anexar.type = 'button';
      anexar.title = 'Imagens, vídeos ou PDF (pode escolher vários)';
      lista.appendChild(anexar);
    }

    caixa.appendChild(lista);

    if (!fixo) {
      var lixeira = criar('button', 'qa-manual-remover');

      lixeira.type = 'button';
      lixeira.title = 'Remover teste manual';
      lixeira.setAttribute('aria-label', 'Remover teste manual');
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
    gravarTestesManuais();
  }

  document.addEventListener('input', atualizarTesteManual);
  document.addEventListener('change', atualizarTesteManual);

  function aoMudarAPagina() {
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
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', traduzir);
  } else {
    traduzir();
  }
})();
