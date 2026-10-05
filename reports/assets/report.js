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
  // mesmo arquivo neste navegador, as escolhas voltam. Não vai junto
  // quando o HTML é enviado a outra pessoa.
  var PREFIXO_CLASSIFICACAO = 'qa-classificacao:' + location.pathname + ':';

  function chaveClassificacao(lista) {
    return (
      PREFIXO_CLASSIFICACAO +
      lista.getAttribute('data-teste') +
      ':' +
      lista.getAttribute('data-campo')
    );
  }

  function lerClassificacao(lista) {
    try {
      return localStorage.getItem(chaveClassificacao(lista)) || '';
    } catch (erro) {
      return '';
    }
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
      .querySelectorAll('select.qa-classificacao:not([data-restaurada])')
      .forEach(function (lista) {
        var valor = lerClassificacao(lista);

        if (valor) {
          lista.value = valor;
        }

        marcarClassificacao(lista);
        lista.setAttribute('data-restaurada', '');
      });
  }

  document.addEventListener('change', function (evento) {
    var lista = evento.target;

    if (lista.classList && lista.classList.contains('qa-classificacao')) {
      gravarClassificacao(lista);
      marcarClassificacao(lista);
    }
  });

  if (window.MutationObserver) {
    new MutationObserver(restaurarClassificacoes).observe(
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
    restaurarClassificacoes();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', traduzir);
  } else {
    traduzir();
  }
})();
