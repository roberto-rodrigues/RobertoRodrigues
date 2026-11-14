# Observatório DF — página Fontes

Mostra de onde vêm os dados do observatório: as fontes oficiais do Distrito Federal e o registro de cada coleta automática.

- `coletor/coletar.py` baixa os arquivos de dados abertos do Portal da Transparência do DF e grava `site/dados/`.
- `site/` é a página estática publicada no GitHub Pages.
- `.github/workflows/coleta-e-publicacao.yml` roda a coleta todo dia e publica o site.

## Rodar na sua máquina

```bash
python coletor/coletar.py
```

```bash
python -m http.server 8000 --directory site
```

Depois abra http://localhost:8000.
