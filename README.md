# Piauí Primeira Infância - análise de conversas WhatsApp

Pipeline de ingestão/classificação (`pipeline/`) + dashboard em Next.js
(`web/`) que le o mesmo `data/whatsapp.db`.

O dashboard não duplica nenhum cálculo: as rotas de API do próprio Next.js
(`web/src/app/api/**/route.ts`) chamam Python sob demanda (`python -m api.cli
...`, ver `api/cli.py` e `api/dashboard_data.py`), que importa e chama as
mesmas funções de `pipeline/metrics.py` usadas pelo resto do pipeline. Não há
servidor Python de longa duração - cada requisição sobe um processo Python,
lê o banco, calcula e termina.

## Rodando o dashboard

Um único comando, a partir da raiz do repo:

```bash
cd web && npm run dev
```

Acesse `http://localhost:3000`. Requer Python (com `requirements.txt`
instalado) disponível no PATH como `python`.

## Testes

```bash
python -m pytest api/tests/
```

Confere que `api/dashboard_data.py` devolve os mesmos números que uma chamada
direta às funções de `pipeline/metrics.py` (garantia de que a camada de
API/filtro não introduziu divergência de cálculo).
