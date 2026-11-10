# ETL com pandas — Limpeza de Inventário de Ativos de TI

Pipeline em **Python/pandas** que pega uma planilha de inventário de TI preenchida à mão (cheia de erros) e entrega dados limpos, validados e prontos para análise no Power BI ou em SQL. **A planilha é fictícia**, gerada por `gerar_dados_sujos.py` para reproduzir problemas reais de planilhas operacionais.

## O problema
Planilhas de controle mantidas por várias pessoas acumulam inconsistências: o mesmo equipamento escrito de cinco jeitos, datas em formatos diferentes, valores como texto, duplicatas e campos vazios. Isso quebra qualquer dashboard ou soma que dependa desses dados.

## Antes e depois

| Campo | Antes (bruto) | Depois (limpo) |
|---|---|---|
| Tipo | `Notebok`, ` Notebook `, `Note book`, `NOTEBOOK` | `Notebook` |
| Data | `25.02.2024`, `04-03-2025`, `2024-02-25`, `31/02/2023` | `2024-02-25` (inválidas são sinalizadas) |
| Valor | `R$ 1.241,55`, `1480,20`, `4175.90`, `R$5.433` | `1241.55`, `1480.2`, `4175.9`, `5433.0` |
| Usuário | `  FÁBIO Souza ` | `Fábio Souza` |
| Status | `em uso`, `EM USO`, `uso` | `Em uso` |
| Marca | `hp`, `lg` | `HP`, `LG` |

## Etapas do pipeline (`etl.py`)
1. **Extract**: lê o CSV exportado do Excel (`;`, UTF-8 com BOM) como texto, sem deixar o pandas adivinhar tipos.
2. **Transform**: padroniza texto, mapeia categorias para valores canônicos, converte datas em 5 formatos e valores em formato brasileiro e americano, e remove duplicatas exatas e "disfarçadas" (mesmo patrimônio e série depois da padronização).
3. **Validate**: em vez de apagar registros problemáticos, cria uma coluna `problemas` e separa os **críticos** (data inválida ou futura, valor ausente ou negativo, tipo desconhecido) dos **alertas** (e-mail inválido, departamento vazio).
4. **Load**: grava o CSV limpo, o CSV de rejeitados (para correção na origem), uma tabela SQLite e um relatório de qualidade em Markdown.

## Resultado na base de exemplo
| Métrica | Valor |
|---|---|
| Linhas na planilha bruta | 635 |
| Duplicatas removidas | 35 |
| Registros válidos | 571 |
| Rejeitados por problema crítico | 29 |

Detalhes em [`saida/relatorio_qualidade.md`](saida/relatorio_qualidade.md).

## Estrutura
```
├── dados/inventario_ativos_bruto.csv   # planilha suja (fictícia)
├── saida/
│   ├── inventario_limpo.csv
│   ├── inventario_rejeitados.csv
│   └── relatorio_qualidade.md
├── tests/test_etl.py      # testes das regras de limpeza (pytest)
├── etl.py                 # pipeline
├── gerar_dados_sujos.py   # gera a planilha de exemplo
└── requirements.txt
```

## Como executar
```bash
pip install -r requirements.txt
python gerar_dados_sujos.py   # opcional: recria a planilha bruta
python etl.py
pytest -q
```

## Decisões
- **Não apagar silenciosamente**: registro com problema vai para um arquivo de rejeitados com o motivo, para que a origem seja corrigida.
- **Regras explícitas** (dicionários de mapeamento) em vez de "adivinhação", para que qualquer pessoa entenda e mantenha.
- **Funções pequenas e testadas**: cada regra de conversão tem teste.

## Tecnologias
Python · pandas · SQLite · pytest

## Autor
**Artur Martins** · [LinkedIn](https://www.linkedin.com/in/artur-martins) · [GitHub](https://github.com/arturmartinsgo)
