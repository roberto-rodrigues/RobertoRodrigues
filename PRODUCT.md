# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

delegated: coletor em Python (biblioteca padrão) + site estático em HTML/CSS/JS, publicado no GitHub Pages. Escolhido porque a página é só de leitura, sem login nem escrita pelo visitante, e o registro de coletas fica versionado no git.

## Users

Cidadãos do Distrito Federal, leigos em orçamento público, que querem saber de onde vêm os números e se podem confiar neles.

## Product Purpose

Observatório cívico do Distrito Federal. A primeira entrega é a página Fontes: lista as fontes oficiais usadas e mostra o registro auditável de cada coleta automática.

## Positioning

A procedência é demonstrada, não declarada: cada selo de verificação vem de uma coleta registrada, com data, quantidade de registros e link para o arquivo original.

## Capabilities and Constraints

- Coleta automática apenas do Portal da Transparência do DF (arquivos de dados abertos de receita e despesa).
- Demais fontes (Dados Abertos DF, TCDF, CLDF, TSE, IBGE) entram como consulta manual até terem coletor.
- Não usar a API interna do portal, que exige identificador de cliente.
- Em aberto: nome definitivo do projeto ("Observatório DF" é provisório) e as demais páginas.

## Brand Commitments

Referência de funcionalidade indicada pelo usuário: fiscalizaguarulhos.vercel.app/fontes.

## Evidence on Hand

Dados reais em `site/dados/`, gerados por `coletor/coletar.py`. Nenhum número do DF deve ser escrito à mão.

## Product Principles

1. Todo número aponta para o arquivo de onde saiu.
2. Falha de coleta e mês ainda não publicado são situações diferentes e aparecem como tal.
3. Fonte sem coleta registrada não recebe selo de verificada.
4. Linguagem de cidadão, não de contador.

## Accessibility & Inclusion

Legível no celular; situação nunca indicada só por cor; navegação anônima, sem cadastro nem rastreamento.
