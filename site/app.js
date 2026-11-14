(() => {
  "use strict";

  const FUSO = "America/Sao_Paulo";
  const fmtData = new Intl.DateTimeFormat("pt-BR", { timeZone: FUSO, day: "2-digit", month: "2-digit", year: "numeric" });
  const fmtHora = new Intl.DateTimeFormat("pt-BR", { timeZone: FUSO, hour: "2-digit", minute: "2-digit" });
  const fmtNum = new Intl.NumberFormat("pt-BR");
  const MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"];

  const ICONES = {
    ok: '<path d="M3.5 8.5l3 3 6-7"/>',
    espera: '<circle cx="8" cy="8" r="5.5"/><path d="M8 5v3.2l2 1.3"/>',
    falha: '<path d="M4 4l8 8M12 4l-8 8"/>',
  };
  const SITUACOES = {
    concluida: { tipo: "ok", texto: "Concluída" },
    nao_publicada: { tipo: "espera", texto: "Ainda não publicada" },
    falhou: { tipo: "falha", texto: "Falhou" },
  };

  /** Cria um elemento; filhos em texto entram como texto, nunca como HTML. */
  function el(tag, atributos = {}, ...filhos) {
    const no = document.createElement(tag);
    for (const [chave, valor] of Object.entries(atributos)) {
      if (valor === false || valor == null) continue;
      if (chave === "class") no.className = valor; else no.setAttribute(chave, valor === true ? "" : valor);
    }
    no.append(...filhos.filter((f) => f != null && f !== false));
    return no;
  }
  function selo(tipo, texto) {
    const no = el("span", { class: `selo selo--${tipo}` });
    if (ICONES[tipo]) no.innerHTML = `<svg aria-hidden="true" viewBox="0 0 16 16">${ICONES[tipo]}</svg>`;
    no.append(texto);
    return no;
  }
  const externo = (texto, url) => el("a", { href: url, rel: "noopener" }, texto, el("span", { "aria-hidden": "true" }, " ↗"));
  const data = (iso) => fmtData.format(new Date(iso));
  const dataHora = (iso) => `${fmtData.format(new Date(iso))} às ${fmtHora.format(new Date(iso))}`;
  const mesAno = (c) => `${MESES[Number(c.slice(5)) - 1]} de ${c.slice(0, 4)}`;
  const mesCurto = (c) => `${c.slice(5)}/${c.slice(0, 4)}`;

  const estado = { fontes: null, registro: [], filtroFonte: "todas", soPendencias: false };

  function desenharFontes() {
    const area = document.getElementById("fontes-automaticas");
    area.replaceChildren(...estado.fontes.automaticas.map((fonte) => {
      const e = fonte.estado;
      const falhou = e.situacao === "falhou";
      const fatos = el("dl", { class: "fatos" });
      const fato = (rotulo, valor, destaque) => fatos.append(el("div", { class: destaque ? "destaque" : null }, el("dt", {}, rotulo), el("dd", {}, valor)));
      if (e.registros != null) fato(`Registros em ${estado.fontes.exercicio}`, el("span", {}, fmtNum.format(e.registros), el("small", {}, ` ${fonte.unidade}`)), true);
      if (e.cobertura) fato("Meses publicados", `${MESES[Number(e.cobertura[0].slice(5)) - 1]} a ${mesAno(e.cobertura[1])}`);
      if (e.arquivo_atualizado_em) fato("Arquivo atualizado pela fonte em", dataHora(e.arquivo_atualizado_em));
      if (e.ultima_coleta) fato("Última coleta com sucesso", dataHora(e.ultima_coleta));
      return el("article", { class: "fonte" },
        el("p", { class: "fonte__orgao" }, fonte.sigla),
        el("div", { class: "fonte__cabeca" },
          el("h3", {}, fonte.nome),
          falhou ? selo("falha", "Falha na última coleta") : selo("ok", `Verificada em ${data(e.ultima_coleta)}`)),
        falhou && el("p", { class: "erro-fonte" }, `A coleta de ${dataHora(e.ultima_tentativa)} não funcionou: ${e.detalhe}. Os números abaixo são da última coleta com sucesso.`),
        el("p", { class: "fonte__texto" }, fonte.coleta),
        el("p", { class: "fonte__texto" }, fonte.uso),
        fatos,
        el("ul", { class: "fonte__links" },
          el("li", {}, externo("Abrir no portal oficial", fonte.url_portal)),
          el("li", {}, el("a", { href: fonte.url_arquivo }, "Baixar o arquivo original (.zip)")),
          el("li", {}, externo("Dicionário de dados", fonte.url_dicionario))));
    }));
  }

  function desenharFiltro() {
    const opcoes = [["todas", "Todas"], ...estado.fontes.automaticas.map((f) => [f.id, f.nome.split(" do ")[0]])];
    document.getElementById("filtro-fonte").replaceChildren(...opcoes.map(([id, rotulo]) => {
      const botao = el("button", { type: "button", "aria-pressed": String(estado.filtroFonte === id) }, rotulo);
      botao.addEventListener("click", () => { estado.filtroFonte = id; desenharFiltro(); desenharRegistro(); });
      return botao;
    }));
  }

  function periodoColetas(linha) {
    if (linha.execucoes === 1) return dataHora(linha.ultima_coleta);
    const inicio = data(linha.primeira_coleta), fim = data(linha.ultima_coleta);
    return `${inicio === fim ? fim : `${inicio} a ${fim}`} · ${fmtNum.format(linha.execucoes)} coletas iguais`;
  }

  function desenharRegistro() {
    const nomes = Object.fromEntries(estado.fontes.automaticas.map((f) => [f.id, f]));
    const maximos = {};
    for (const l of estado.registro) maximos[l.fonte] = Math.max(maximos[l.fonte] || 0, l.registros || 0);

    const linhas = estado.registro
      .filter((l) => estado.filtroFonte === "todas" || l.fonte === estado.filtroFonte)
      .filter((l) => !estado.soPendencias || l.situacao !== "concluida")
      .sort((a, b) => (b.competencia || "9999").localeCompare(a.competencia || "9999")
        || b.ultima_coleta.localeCompare(a.ultima_coleta) || a.fonte.localeCompare(b.fonte));

    let mesAnterior;
    const corpo = document.getElementById("linhas-registro");
    corpo.replaceChildren(...linhas.map((l) => {
      const fonte = nomes[l.fonte];
      const situacao = SITUACOES[l.situacao] || { tipo: "neutro", texto: l.situacao };
      const mudou = mesAnterior !== undefined && mesAnterior !== l.competencia;
      mesAnterior = l.competencia;
      const quantidade = l.registros == null ? "—" : fmtNum.format(l.registros);
      return el("tr", { class: mudou ? "mudou-mes" : null },
        el("td", { class: "c-mes mes" }, l.competencia ? mesCurto(l.competencia) : "Arquivo inteiro"),
        el("td", { class: "c-fonte" }, fonte ? fonte.nome.split(" — ")[0] : l.fonte, el("span", { class: "apoio" }, fonte ? ` ${fonte.unidade}` : "")),
        el("td", { class: "c-qtd num" }, el("span", { class: "qtd" }, quantidade),
          l.registros ? el("span", { class: "barra", style: `width:${Math.max(2, Math.round(100 * l.registros / maximos[l.fonte]))}%` }) : null),
        el("td", { class: "c-sit" }, selo(situacao.tipo, situacao.texto), l.detalhe ? el("span", { class: "motivo" }, l.detalhe) : null),
        el("td", { class: "c-arq" }, l.arquivo_atualizado_em ? data(l.arquivo_atualizado_em) : "sem arquivo lido"),
        el("td", { class: "c-col" }, periodoColetas(l)));
    }));
    document.querySelector(".tabela-area").hidden = linhas.length === 0;
    document.getElementById("registro-vazio").hidden = linhas.length !== 0;
  }

  function desenharManuais() {
    document.getElementById("fontes-manuais").replaceChildren(...estado.fontes.manuais.map((f) =>
      el("li", {},
        el("span", { class: "sigla" }, f.sigla),
        el("div", {}, el("p", { class: "nome" }, f.nome), el("p", { class: "uso" }, f.uso)),
        el("div", { class: "acoes" }, selo("neutro", "Consulta manual"), externo("Abrir o portal", f.url_portal)))));
  }

  function desenharEstadoGeral() {
    const coletas = estado.fontes.automaticas.map((f) => f.estado);
    const falhas = coletas.filter((e) => e.situacao === "falhou").length;
    const no = document.getElementById("estado-geral");
    no.replaceChildren("Última coleta: ", el("strong", {}, dataHora(estado.fontes.gerado_em)), ". ",
      falhas ? `${falhas} de ${coletas.length} fontes falharam nessa coleta.` : `As ${coletas.length} fontes automáticas responderam.`);
    const licenca = estado.fontes.licenca;
    document.getElementById("licenca").replaceChildren("Dados do Portal da Transparência do Distrito Federal, sob a licença ", externo(licenca.nome, licenca.url), ".");
  }

  async function carregar(caminho) {
    const resposta = await fetch(caminho, { cache: "no-cache" });
    if (!resposta.ok) throw new Error(`${caminho}: HTTP ${resposta.status}`);
    return resposta.json();
  }

  async function iniciar() {
    try {
      [estado.fontes, estado.registro] = await Promise.all([carregar("dados/fontes.json"), carregar("dados/sincronizacoes.json")]);
    } catch (erro) {
      document.getElementById("estado-geral").textContent = "";
      const aviso = el("p", { class: "aviso", role: "alert" }, "Não foi possível carregar o registro de coletas. Recarregue a página; se o erro continuar, os arquivos em dados/ ainda não foram gerados pelo coletor.");
      document.getElementById("fontes-automaticas").replaceChildren(aviso);
      document.getElementById("linhas-registro").replaceChildren();
      console.error(erro);
      return;
    }
    desenharEstadoGeral(); desenharFontes(); desenharFiltro(); desenharRegistro(); desenharManuais();
    document.getElementById("filtro-pendencias").addEventListener("change", (e) => { estado.soPendencias = e.target.checked; desenharRegistro(); });
    document.getElementById("limpar-filtros").addEventListener("click", () => {
      estado.filtroFonte = "todas"; estado.soPendencias = false;
      document.getElementById("filtro-pendencias").checked = false;
      desenharFiltro(); desenharRegistro();
    });
  }

  iniciar();
})();
