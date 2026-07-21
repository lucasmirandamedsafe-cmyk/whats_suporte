---
name: ingest-whatsapp-export
description: Ingest a newly added WhatsApp export folder or zip (group chat or 1:1 support conversations) into the analise_chats pipeline - unzip, place in the right raw/ location, run the right parse/classify scripts, reindex search, and verify against the dashboard. Use whenever the user says they added new raw messages, a new export, a new zip, or a new pasta with WhatsApp data.
---

# Ingerir novo export do WhatsApp

Este projeto tem **dois pipelines separados** dependendo do tipo de dado. Identifique
qual se aplica ANTES de rodar qualquer script - eles alimentam tabelas e paginas
diferentes do dashboard.

## 1. Qual pipeline usar?

| Sinal | Pipeline | Vai para | Pagina do dashboard |
|---|---|---|---|
| Conversa 1:1 entre um cidadao e o numero de suporte | `parse.py` -> `enrich_ai.py` | `messages` / `sessions` | `dashboard/app.py` (Suporte WhatsApp) |
| Grupo de WhatsApp (varias pessoas, coordenacao/supervisoras) | `parse_groups.py` -> `classify_issues.py` -> `classify_tipo_erro.py` | `group_messages` | `dashboard/pages/1_Grupos.py` |

Confira o nome do arquivo exportado (ex: `WhatsApp Chat - <numero de telefone>.zip`
geralmente e 1:1; `WhatsApp Chat - <nome de grupo>.zip` e grupo) e o conteudo (server
varias pessoas falando = grupo).

## 2. Extrair e posicionar os arquivos

Os exports do WhatsApp vem em `.zip` contendo um `_chat.txt` (as vezes com midia junto,
que pode ser ignorada). Os parsers so leem `.txt` soltos nas pastas certas:

- **Grupo**: extrair o `.txt` direto em `raw/<area>/` (area = `assistencia`, `saude` ou
  `educacao`, conforme `config.py` -> `pipeline/parse_groups.py`).
- **1:1 suporte**: extrair o `.txt` direto em `raw/suporte/` (definido em
  `config.RAW_DIR`). **Atencao**: `parse.py` faz `config.RAW_DIR.glob("*.txt")` -
  isso NAO e recursivo. Se os zips estiverem numa subpasta (ex:
  `raw/suporte/suporte_assistencia/`), extraia os `.txt` e MOVA pra
  `raw/suporte/` diretamente, ou o parser nao vai achar nada.

Comando pra extrair todos os zips de uma pasta de uma vez (PowerShell):
```powershell
Get-ChildItem "raw/suporte/suporte_assistencia/*.zip" | ForEach-Object {
    Expand-Archive -Path $_.FullName -DestinationPath "raw/suporte/suporte_assistencia/_tmp_extract" -Force
}
Get-ChildItem "raw/suporte/suporte_assistencia/_tmp_extract" -Filter *.txt -Recurse |
    Move-Item -Destination "raw/suporte/"
```
Renomeie arquivos duplicados (`_chat.txt` de varias conversas 1:1 tem o mesmo nome) -
use o nome do zip original como base, ex: `WhatsApp Chat - <numero>.txt`.

## 3. Configurar quem e o "suporte" (so pipeline 1:1)

Antes de rodar `parse.py`, edite `config.py` -> `SUPPORT_SENDER_NAMES` com o(s) nome(s)
exatos que aparecem nos exports como remetente do lado do suporte (precisa bater com o
texto real do `.txt`, comparacao e por substring case-insensitive). Sem isso,
`first_response_seconds` e o KPI de tempo de resposta ficam errados (tudo tratado como
mensagem de cliente).

## 4. Rodar o pipeline

**1:1 suporte:**
```
python pipeline/parse.py
python pipeline/enrich_ai.py
```

**Grupo:**
```
python pipeline/parse_groups.py
python pipeline/classify_issues.py
python pipeline/classify_tipo_erro.py
```
`classify_issues.py` ja roda o pre-filtro heuristico+semantico
(`pipeline/prefilter_issues.py`) automaticamente antes de gastar chamada da Groq - nao
precisa rodar separado. Se a Groq bater rate limit no meio (mensagem `429` /
`rate_limit_exceeded`), o script deixa `analyzed_at` NULL nas mensagens nao processadas
e e seguro rodar de novo depois (retoma de onde parou). Se a cota nao liberar em tempo
habil, use a skill `review-classification-quality` pra fazer a classificacao
manualmente sem depender da API.

## 5. Reindexar a busca semantica

Sempre que houver mensagens novas em `group_messages`, reindexe:
```
python pipeline/embeddings.py
```
Isso recalcula o TF-IDF e os vetores em `message_embeddings` (usado por
`pipeline/search_messages.py` e pelo pre-filtro semantico). Sem isso o indice fica
desatualizado (mensagens novas ficam sem vetor cacheado, ainda funcionam mas so com
vetorizacao on-the-fly mais lenta).

## 6. Verificar

- `python pipeline/search_messages.py "<algum termo esperado>" --top 5` - confirma que
  as mensagens novas aparecem.
- Rode a pagina do dashboard afetada direto (fora do Streamlit) pra pegar erro de import
  cedo, ja que `curl` no app rodando NAO executa o script da pagina (SPA com roteamento
  client-side - so serve o shell HTML):
  ```
  python -c "import runpy; runpy.run_path('dashboard/pages/1_Grupos.py', run_name='__main__')"
  ```
- Reinicie o Streamlit com cache limpo antes de considerar concluido (o processo antigo
  mantem modulos Python em memoria - editar arquivo sozinho NAO garante reload):
  ```
  # matar o processo antigo (ache o PID escutando 8501), depois:
  find . -iname "__pycache__" -exec rm -rf {} +
  streamlit run dashboard/app.py --server.headless true --server.port 8501
  ```
