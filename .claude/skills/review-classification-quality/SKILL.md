---
name: review-classification-quality
description: Deep manual review to fix false positives or false negatives in is_issue/issue_categoria/issue_tema/issue_tipo classification of group_messages, or to reclassify without depending on the Groq API (rate limits, quota, or prompt quality issues). Use when the user questions specific classified messages, says the counts look wrong/inflated, or when a Groq classification run hits rate limits mid-way.
---

# Revisar/corrigir qualidade da classificacao de group_messages

Contexto: `pipeline/classify_issues.py` usa uma LLM (Groq) pra decidir se cada mensagem
de grupo E uma reclamacao/erro (`is_issue`). Isso e propenso a dois problemas ja vistos
neste projeto: (1) falso positivo quando a LLM marca uma mensagem so por estar dentro de
uma thread sobre um problema, mesmo que o texto dela mesma nao reclame de nada; (2) rate
limit da conta gratuita da Groq (100k tokens/dia) interrompendo a classificacao no meio.

## Criterio de classificacao (use em qualquer revisao manual)

Uma mensagem so e `is_issue=1` se o **proprio texto dela** expressa reclamacao ou relata
erro/problema - nao porque esta no meio de uma conversa sobre um problema.

**NAO conta**, mesmo em contexto de problema:
- Confirmacao de tarefa concluida ("Realizado o cadastro de X")
- Concordancia/resposta neutra ("Pois e", "Isso mesmo", "Ok", "Certo")
- Boilerplate do WhatsApp: entrou/saiu do grupo, figurinha/imagem/video/audio omitido,
  mensagem apagada
- Saudacao pura, agradecimento puro
- Comunicado oficial/informativo da coordenacao (mesmo mencionando "erro" ou "problema"
  no meio do texto) - e aviso, nao reclamacao
- Pergunta de "como fazer X" sem afirmar que algo esta quebrado
- Confirmacao POSITIVA ("Consegui!", "ja estao com certificado") - as vezes a
  classificacao antiga marcou essas por engano, sao o oposto de um problema

**Conta**: qualquer frase que por si so afirma que algo nao funciona, deu erro, sumiu,
esta errado, nao aparece, nao aceita, esta invalido, etc. - mesmo curta ("Não salva",
"ta invalido", "Não aparece os perfis").

## Passo a passo

1. **Backup antes de tudo:**
   ```
   cp data/whatsapp.db "data/whatsapp.db.bak-$(date +%Y%m%d%H%M%S)"
   ```

2. **Reunir candidatos.** Duas fontes possiveis:
   - Mensagens ja marcadas `is_issue=1` (pra auditar falsos positivos existentes).
   - `python pipeline/search_messages.py "<termo>" --top 30` pra achar mensagens
     parecidas com um caso que o usuario apontou, incluindo as que NAO foram marcadas
     (falso negativo).
   Exporte os candidatos pra JSON (id, conversation_id, timestamp, sender, content,
   categoria/tema/tipo atuais) pra revisar em lote sem ida-e-volta ao banco.

3. **Revisar cada candidato** aplicando o criterio acima. Para textos ambiguos/curtos,
   olhe se ha contexto na mesma conversa (mesmo assim, so mantenha se o texto proprio
   sustentar a decisao).

4. **Aplicar as decisoes** direto no banco (sem depender da Groq): para cada
   candidato mantido, `UPDATE group_messages SET is_issue=1, issue_categoria=?,
   issue_tema=?, issue_tipo=?, analyzed_at=datetime('now') WHERE id=?`. Para os
   descartados (e qualquer outra mensagem pendente `analyzed_at IS NULL`), marque
   `is_issue=0` com os demais campos NULL.

5. **Reindexar embeddings** (o texto/rotulo mudou):
   ```
   python pipeline/embeddings.py
   ```

6. **Comparar antes/depois** e reportar pro usuario - use
   `pipeline/metrics.py::kpis_grupos` e `deduplicar_incidentes` pra mostrar totais e
   por categoria/tipo antes vs. depois da revisao, igual ao formato que ja usamos
   nessa conversa (tabela markdown com "Antes" / "Agora").

7. **Conferir o dashboard** - ver a skill `ingest-whatsapp-export`, secao 6. O dashboard
   Next.js (`cd web && npm run dev`) chama Python sob demanda a cada requisicao, sem
   cache nem processo de longa duracao - basta atualizar a pagina.

## Se a Groq estiver rate-limited e voce precisar classificar do zero

Nao espere horas: reaproveite a classificacao antiga (solta demais, mas raramente
esquece problema real) como lista de candidatos de alta revocacao, e faca a revisao
manual acima em cima dela - foi assim que 341 candidatos da Groq viraram 157 decisoes
manuais nessa conversa, sem gastar nenhuma chamada de API nova.
