# Página "Fontes" — Observatório do Distrito Federal

> Especificação derivada da análise da página pública
> `https://fiscalizaguarulhos.vercel.app/fontes` (lida em 13–14/11/2026).
> Só o que o site expõe publicamente foi observado; o que roda no servidor é inferência e está marcado como tal.

## 1. O que a página de referência faz

A página responde a uma pergunta do cidadão: **"de onde vêm estes números e posso confiar neles?"**
Ela tem dois blocos.

### 1.1 Cartões de fontes oficiais

Quatro cartões, um por instituição. Cada cartão traz:

| Elemento | Exemplo na referência |
|---|---|
| Sigla da fonte | `TCE-SP / Audesp` |
| Selo de estado | `✓ Base Verificada` |
| Nome completo da instituição e recorte | Tribunal de Contas do Estado de São Paulo — Painel Guarulhos |
| O que foi coletado, com números | Receitas (R$ 5,74 bi) e pagamentos (R$ 4,28 bi · 28.882 ordens bancárias) |
| Para que o dado serve no site | "Fornece os dados contábeis oficiais enviados mensalmente…" |
| Link para o portal visual da instituição | "Abrir Painel Visual do TCE-SP ↗" |

O texto promete links para os **portais visuais**, "sem códigos ou JSON bruto": o público-alvo é leigo.

### 1.2 Registro de sincronizações automáticas — a funcionalidade de destaque

Tabela com o histórico das coletas automáticas. Colunas:

| Coluna | Conteúdo |
|---|---|
| Competência | mês/ano do dado (ex.: `09/2026`) |
| Fonte oficial | identificador do coletor (ex.: `tcesp-despesas`) |
| Data da coleta | dia em que o robô rodou |
| Registros auditados | quantidade de linhas importadas |
| Status | `✓ Concluído` ou `vazio` |

Observado: uma execução por dia, cobrindo as três competências mais recentes; meses que a fonte ainda não publicou aparecem como `vazio` com 0 registros. As 20 execuções mais recentes ficam visíveis.

Por que isso se destaca: transforma "confie em nós" em evidência. O cidadão vê quando a coleta rodou, quantos registros vieram e quais meses a fonte ainda não publicou.

**Inferência (não observável):** um agendador diário grava uma linha por (fonte, competência) em uma tabela de log, e a página lê as últimas linhas dessa tabela.

### 1.3 Fraquezas da referência a não repetir

- Só uma das quatro fontes aparece no registro (`tcesp-despesas`); Câmara, TSE e IBGE têm selo "verificada" sem nenhuma coleta registrada.
- `vazio` não explica a causa (a fonte ainda não publicou o mês? a coleta falhou?). Falha e ausência de dado precisam ser estados diferentes.
- Linhas repetidas dia após dia sem agrupamento: 20 linhas dizem o que 3 diriam.
- O selo "Base Verificada" não informa quem verificou nem quando.

## 2. Equivalente para o Distrito Federal

O DF acumula competências de estado e de município, então as instituições mudam:

| Papel na referência | Guarulhos | Distrito Federal | Estado da verificação |
|---|---|---|---|
| Contas públicas (receitas e pagamentos) | TCE-SP / Audesp | Portal da Transparência do DF — `transparencia.df.gov.br` | **No ar** (lido em 14/11/2026: despesas por área, arrecadação por imposto, dados "atualizados em 30/10/2026"). Endpoints de API ainda não confirmados. |
| Catálogo de dados abertos | — | Portal de Dados Abertos do DF — `dados.df.gov.br` (CKAN) | **Não confirmado**: timeout nas tentativas de leitura. |
| Controle externo | TCE-SP | TCDF — `www2.tc.df.gov.br` | **No ar** (tem seção "Transparência Fiscal" e painel de indícios de irregularidades). Dados reutilizáveis ainda não confirmados. |
| Poder Legislativo | Câmara Municipal (34 vereadores) | Câmara Legislativa do DF — `cl.df.gov.br` (24 deputados distritais) | **Não confirmado**: timeout. |
| Eleições | TSE 2024 (municipais) | TSE 2022 (gerais: governador e deputados distritais) | **Não confirmado** nesta sessão. |
| Território e população | IBGE 3518800 | IBGE 5300108 (Brasília/DF) | **Não confirmado**: timeout. |

Nenhum número do DF (população, valores, contagens) deve ser escrito na página antes de vir de uma coleta real: a página existe para provar procedência.

## 3. Requisitos da página

### Funcionais

- **RF-01** Listar cada fonte oficial do DF em um cartão com: sigla, nome completo, o que é coletado, para que serve, link para o portal visual.
- **RF-02** O estado de cada fonte vem do registro de coletas, não de texto fixo: `verificada em <data>`, `sem coleta ainda`, `falha na última coleta`.
- **RF-03** Exibir o registro de sincronizações com competência, fonte, data da coleta, registros e status.
- **RF-04** Distinguir três resultados de coleta: `concluída` (com registros), `ainda não publicada pela fonte` (resposta válida, zero registros) e `falhou` (erro de rede ou de formato), com o motivo.
- **RF-05** Agrupar execuções idênticas consecutivas (mesma fonte, competência, contagem e status) em uma linha com o intervalo de datas.
- **RF-06** Toda fonte com selo aparece no registro; fonte sem coletor automatizado é rotulada como "consulta manual".
- **RF-07** Cada linha do registro leva ao dado bruto correspondente na fonte, para quem quiser conferir.

### Não funcionais

- **RNF-01** Navegação anônima, sem cadastro e sem rastreamento.
- **RNF-02** Legível em celular; a tabela não pode exigir rolagem horizontal para a informação principal.
- **RNF-03** Acessível (contraste, leitura por leitor de tela, status nunca só por cor).
- **RNF-04** A página abre mesmo se a coleta do dia falhar: lê o último registro gravado.

## 4. Decisão de tecnologia (delegada pelo usuário)

**Coletor em Python + site estático.**

- Um script Python consulta cada fonte, grava os dados e acrescenta uma linha ao registro (`sync-log.json`).
- Um agendamento diário (GitHub Actions) roda o script e publica os arquivos.
- A página é HTML/CSS/JS estático que lê `fontes.json` e `sync-log.json`.

Motivo: o escopo é uma página só de leitura, sem login nem escrita pelo usuário; não precisa de servidor nem de banco. O registro de coletas fica versionado no git, o que por si só o torna auditável.

## 5. Em aberto

1. Confirmar os endpoints de dados de cada fonte do DF (item 2) a partir de um ambiente com acesso de rede a elas.
2. Nome e identidade do projeto (a referência usa "Fiscaliza Guarulhos").
3. Quais fontes entram na primeira versão com coleta automática e quais ficam como "consulta manual".
