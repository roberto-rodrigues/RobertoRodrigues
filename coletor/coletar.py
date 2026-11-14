#!/usr/bin/env python3
"""Coletor da página Fontes (Distrito Federal).

Baixa os arquivos de dados abertos do Portal da Transparência do DF,
conta os registros por competência (mês) e grava:

  site/dados/fontes.json          catálogo das fontes e estado da última coleta
  site/dados/sincronizacoes.json  registro auditável das coletas

Só usa a biblioteca padrão. Uso:  python coletor/coletar.py [--ano 2026]
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
import urllib.error
import urllib.request
import zipfile
from collections import Counter
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from zoneinfo import ZoneInfo

FUSO = ZoneInfo("America/Sao_Paulo")
PORTAL = "https://www.transparencia.df.gov.br"
AGENTE = "coletor-fontes-df/0.1 (dados abertos; uso civico)"
RAIZ = Path(__file__).resolve().parent.parent
CACHE = RAIZ / ".cache"


def meses_receita(arquivo: io.BufferedIOBase) -> Counter:
    """Receita_AAAA.csv: separador ';', mês na coluna IN_MES."""
    texto = io.TextIOWrapper(arquivo, encoding="latin-1", newline="")
    leitor = csv.reader(texto, delimiter=";", quoting=csv.QUOTE_NONE)
    cabecalho = next(leitor)
    i_ano, i_mes = cabecalho.index("AA_EXERCICIO"), cabecalho.index("IN_MES")
    contagem: Counter = Counter()
    for linha in leitor:
        if len(linha) != len(cabecalho):
            raise ValueError(f"linha com {len(linha)} colunas, esperado {len(cabecalho)}")
        contagem[f"{linha[i_ano]}-{int(linha[i_mes]):02d}"] += 1
    return contagem


def meses_pagamento(arquivo: io.BufferedIOBase) -> Counter:
    """Despesa_Pagamento_AAAA.csv: separador '¨', data de emissão dd/mm/aaaa."""
    texto = io.TextIOWrapper(arquivo, encoding="latin-1", newline="")
    leitor = csv.reader(texto, delimiter="\xa8", quoting=csv.QUOTE_NONE)
    cabecalho = [c.strip('"') for c in next(leitor)]
    i_data = cabecalho.index("EMISSÃO")
    contagem: Counter = Counter()
    for linha in leitor:
        data = linha[i_data].strip('"') if len(linha) == len(cabecalho) else ""
        if not re.fullmatch(r"\d{2}/\d{2}/\d{4}", data):
            raise ValueError(f"linha fora do formato esperado: {linha[:3]}")
        contagem[f"{data[6:10]}-{data[3:5]}"] += 1
    return contagem


def fontes_automaticas(ano: int) -> list[dict]:
    return [
        {
            "id": "tdf-receita",
            "sigla": "Portal da Transparência do DF",
            "nome": f"Receita do Distrito Federal — exercício {ano}",
            "coleta": "Linhas de receita prevista e realizada, por órgão, natureza e mês.",
            "uso": "Mostra de onde vem o dinheiro do DF: impostos, transferências e demais receitas.",
            "unidade": "linhas de receita",
            "url_arquivo": f"{PORTAL}/arquivos/portal-dados-abertos/Receita_{ano}.zip",
            "membro": f"Receita_{ano}.csv",
            "leitor": meses_receita,
            "url_portal": f"{PORTAL}/#/receita",
            "url_dicionario": "http://dados.df.gov.br/dataset/c92c427a-9f63-4f53-a0dd-ba5d309f0455/resource/13f7c230-8e8c-419d-8675-6bb8e8c9f46d/download/dicionario-de-dados-abertosreceita.pdf",
        },
        {
            "id": "tdf-pagamentos",
            "sigla": "Portal da Transparência do DF",
            "nome": f"Pagamentos do Distrito Federal — exercício {ano}",
            "coleta": "Ordens bancárias emitidas: data, órgão pagador, credor, processo e valor.",
            "uso": "Mostra para quem o governo do DF pagou, quanto e quando.",
            "unidade": "ordens bancárias",
            "url_arquivo": f"{PORTAL}/arquivos/portal-dados-abertos/Despesa_{ano}.zip",
            "membro": f"Despesa_{ano}/Despesa_Pagamento_{ano}.csv",
            "leitor": meses_pagamento,
            "url_portal": f"{PORTAL}/#/despesas",
            "url_dicionario": "http://dados.df.gov.br/dataset/8dce6486-3295-47c3-b463-8a2aaef0ef0b/resource/61a4a81d-73e4-4665-bd85-d6453a98fe47/download/dicionario-de-dados-abertosdespesa.pdf",
        },
    ]


# Fontes oficiais que ainda não têm coleta automática: entram só como link.
FONTES_MANUAIS = [
    {"id": "dados-df", "sigla": "Dados Abertos DF", "nome": "Portal de Dados Abertos do Distrito Federal",
     "uso": "Catálogo geral de bases do governo do DF (terceirizados, imóveis alugados, renúncias fiscais).",
     "url_portal": "https://dados.df.gov.br/"},
    {"id": "tcdf", "sigla": "TCDF", "nome": "Tribunal de Contas do Distrito Federal",
     "uso": "Fiscalização externa das contas do governo e da Câmara Legislativa.",
     "url_portal": "https://www2.tc.df.gov.br/transparenciafiscal/"},
    {"id": "cldf", "sigla": "CLDF", "nome": "Câmara Legislativa do Distrito Federal",
     "uso": "Deputados distritais, comissões e proposições.",
     "url_portal": "https://www.cl.df.gov.br/"},
    {"id": "tse", "sigla": "TSE", "nome": "Tribunal Superior Eleitoral — DivulgaCandContas",
     "uso": "Candidaturas, votação e prestação de contas eleitorais no DF.",
     "url_portal": "https://divulgacandcontas.tse.jus.br/"},
    {"id": "ibge", "sigla": "IBGE", "nome": "Instituto Brasileiro de Geografia e Estatística",
     "uso": "População e território oficiais do DF, usados para calcular valores por habitante.",
     "url_portal": "https://cidades.ibge.gov.br/brasil/df/panorama"},
]


def baixar(url: str, destino: Path, etag_anterior: str | None) -> dict:
    """Baixa o arquivo, a menos que o ETag não tenha mudado e a cópia local exista."""
    pedido = urllib.request.Request(url, headers={"User-Agent": AGENTE})
    if etag_anterior and destino.exists():
        pedido.add_header("If-None-Match", etag_anterior)
    try:
        with urllib.request.urlopen(pedido, timeout=300) as resposta:
            destino.parent.mkdir(parents=True, exist_ok=True)
            with open(destino, "wb") as saida:
                while bloco := resposta.read(1 << 20):
                    saida.write(bloco)
            cabecalhos = resposta.headers
    except urllib.error.HTTPError as erro:
        if erro.code != 304:
            raise
        return {"alterado": False, "etag": etag_anterior}
    modificado = cabecalhos.get("Last-Modified")
    return {
        "alterado": True,
        "etag": cabecalhos.get("ETag"),
        "arquivo_atualizado_em": parsedate_to_datetime(modificado).astimezone(FUSO).isoformat(timespec="minutes") if modificado else None,
    }


def registrar(registro: list[dict], novo: dict, agora: str) -> None:
    """Coletas idênticas e consecutivas viram uma linha só, com intervalo e contagem."""
    chaves = ("fonte", "competencia", "registros", "situacao", "detalhe", "arquivo_atualizado_em")
    for anterior in reversed(registro):
        if (anterior["fonte"], anterior["competencia"]) == (novo["fonte"], novo["competencia"]):
            if all(anterior.get(c) == novo.get(c) for c in chaves):
                anterior["ultima_coleta"] = agora
                anterior["execucoes"] += 1
                return
            break
    registro.append({**novo, "primeira_coleta": agora, "ultima_coleta": agora, "execucoes": 1})


def coletar(fonte: dict, estado: dict, registro: list[dict], ano: int, agora: datetime) -> dict:
    carimbo = agora.isoformat(timespec="minutes")
    zip_local = CACHE / Path(fonte["url_arquivo"]).name
    try:
        baixado = baixar(fonte["url_arquivo"], zip_local, estado.get("etag"))
        if baixado["alterado"] or "contagem" not in estado:
            with zipfile.ZipFile(zip_local) as pacote, pacote.open(fonte["membro"]) as arquivo:
                contagem = dict(fonte["leitor"](arquivo))
            atualizado = baixado.get("arquivo_atualizado_em") or estado.get("arquivo_atualizado_em")
        else:
            contagem, atualizado = estado["contagem"], estado.get("arquivo_atualizado_em")
    except Exception as erro:  # rede, zip corrompido ou formato inesperado: tudo vira "falhou"
        detalhe = f"{type(erro).__name__}: {erro}"[:200]
        registrar(registro, {"fonte": fonte["id"], "competencia": None, "registros": None,
                             "situacao": "falhou", "detalhe": detalhe,
                             "arquivo_atualizado_em": estado.get("arquivo_atualizado_em")}, carimbo)
        return {**estado, "situacao": "falhou", "detalhe": detalhe, "ultima_tentativa": carimbo}

    ultimo_mes = agora.month if ano == agora.year else 12
    for mes in range(1, ultimo_mes + 1):
        competencia = f"{ano}-{mes:02d}"
        quantidade = contagem.get(competencia, 0)
        registrar(registro, {"fonte": fonte["id"], "competencia": competencia, "registros": quantidade,
                             "situacao": "concluida" if quantidade else "nao_publicada", "detalhe": None,
                             "arquivo_atualizado_em": atualizado}, carimbo)
    publicados = sorted(c for c in contagem if c.startswith(str(ano)) and contagem[c])
    return {
        "situacao": "verificada", "detalhe": None,
        "etag": baixado["etag"], "arquivo_atualizado_em": atualizado,
        "ultima_tentativa": carimbo, "ultima_coleta": carimbo,
        "registros": sum(contagem.values()), "contagem": contagem,
        "cobertura": [publicados[0], publicados[-1]] if publicados else None,
    }


def main() -> int:
    argumentos = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    argumentos.add_argument("--ano", type=int, default=datetime.now(FUSO).year)
    argumentos.add_argument("--saida", type=Path, default=RAIZ / "site" / "dados")
    opcoes = argumentos.parse_args()
    agora = datetime.now(FUSO)

    caminho_fontes = opcoes.saida / "fontes.json"
    caminho_registro = opcoes.saida / "sincronizacoes.json"
    anterior = json.loads(caminho_fontes.read_text("utf-8")) if caminho_fontes.exists() else {}
    estados = {f["id"]: f.get("estado", {}) for f in anterior.get("automaticas", [])}
    registro = json.loads(caminho_registro.read_text("utf-8")) if caminho_registro.exists() else []

    automaticas = []
    for fonte in fontes_automaticas(opcoes.ano):
        estado = coletar(fonte, estados.get(fonte["id"], {}), registro, opcoes.ano, agora)
        publica = {k: v for k, v in fonte.items() if k not in ("leitor", "membro")}
        automaticas.append({**publica, "estado": estado})
        print(f"{fonte['id']}: {estado['situacao']}" + (f" — {estado['detalhe']}" if estado.get("detalhe") else f" ({estado['registros']} registros)"))

    opcoes.saida.mkdir(parents=True, exist_ok=True)
    caminho_fontes.write_text(json.dumps({
        "gerado_em": agora.isoformat(timespec="minutes"), "exercicio": opcoes.ano,
        "licenca": {"nome": "Creative Commons BY-SA 4.0", "url": "https://creativecommons.org/licenses/by-sa/4.0/deed.pt_BR"},
        "automaticas": automaticas, "manuais": FONTES_MANUAIS,
    }, ensure_ascii=False, indent=1) + "\n", "utf-8")
    caminho_registro.write_text(json.dumps(registro, ensure_ascii=False, indent=1) + "\n", "utf-8")
    return 1 if any(f["estado"]["situacao"] == "falhou" for f in automaticas) else 0


if __name__ == "__main__":
    sys.exit(main())
