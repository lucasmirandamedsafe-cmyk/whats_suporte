import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from groq import Groq

import config
from pipeline.db import get_conn
from pipeline.prefilter_issues import run as run_prefilter

BATCH_SIZE = 30

CATEGORIAS = ["erro_app", "processo_publico", "outro"]

TOOL = {
    "type": "function",
    "function": {
        "name": "reportar_problemas",
        "description": (
            "Reporta quais mensagens de uma conversa de grupo indicam reclamacao ou "
            "erro/problema na plataforma Piaui Primeira Infancia (app de acompanhamento "
            "de saude, educacao e assistencia social na primeira infancia)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "problemas": {
                    "type": "array",
                    "description": (
                        "Uma entrada para cada mensagem que, por si so, EXPRESSA uma "
                        "reclamacao ou relata um erro/problema. Nao inclua uma mensagem so "
                        "porque ela esta no meio de uma conversa sobre um problema - o "
                        "texto DELA precisa conter a reclamacao/erro. Mensagens normais "
                        "(saudacao, duvida simples, confirmacao de tarefa concluida, "
                        "aviso/comunicado oficial, elogio, resposta neutra tipo 'ok'/'sim'/"
                        "'entendido') NAO entram aqui, mesmo que a conversa ao redor seja "
                        "sobre um problema."
                    ),
                    "items": {
                        "type": "object",
                        "properties": {
                            "indice": {
                                "type": ["integer", "string"],
                                "description": "indice da mensagem na lista",
                            },
                            "categoria": {
                                "type": "string",
                                "description": f"uma de: {', '.join(CATEGORIAS)}",
                            },
                            "tema": {"type": "string", "description": "resumo do problema em 3-6 palavras"},
                        },
                        "required": ["indice", "categoria"],
                    },
                }
            },
            "required": ["problemas"],
        },
    },
}


def _fetch_pending(conn, area=None):
    query = (
        "SELECT id, area, conversation_id, sender, content FROM group_messages "
        "WHERE is_media = 0 AND analyzed_at IS NULL"
    )
    params = ()
    if area:
        query += " AND area = ?"
        params = (area,)
    query += " ORDER BY conversation_id, timestamp"
    return conn.execute(query, params).fetchall()


def _batches_by_conversation(rows):
    by_conv = {}
    for row in rows:
        by_conv.setdefault(row["conversation_id"], []).append(row)
    for conv_id, conv_rows in by_conv.items():
        for i in range(0, len(conv_rows), BATCH_SIZE):
            yield conv_id, conv_rows[i : i + BATCH_SIZE]


def classify_batch(client, rows, model):
    listagem = "\n".join(f"{i}. {r['sender']}: {r['content']}" for i, r in enumerate(rows))
    response = client.chat.completions.create(
        model=model,
        max_tokens=1500,
        tools=[TOOL],
        tool_choice={"type": "function", "function": {"name": "reportar_problemas"}},
        messages=[
            {
                "role": "user",
                "content": (
                    "As mensagens abaixo sao de um grupo/conversa de WhatsApp ligado ao "
                    "programa Piaui Primeira Infancia (acompanhamento de saude, educacao e "
                    "assistencia social na primeira infancia). Aponte SOMENTE as mensagens "
                    "cujo PROPRIO texto e uma reclamacao ou relata um erro/problema na "
                    "plataforma/app/processo.\n\n"
                    "IMPORTANTE: nao marque uma mensagem so por estar dentro de uma thread "
                    "sobre um problema. Cada mensagem e avaliada pelo que ELA MESMA diz.\n\n"
                    "Exemplos que NAO devem ser marcados, mesmo em contexto de problema:\n"
                    "- 'Boa tarde! Realizado o cadastro de Fulano.' (e uma confirmacao de "
                    "tarefa concluida, nao uma reclamacao)\n"
                    "- 'Pois e' / 'Isso mesmo' / 'Ok' / 'Sim' (sao respostas neutras/de "
                    "concordancia, mesmo que a mensagem anterior seja uma reclamacao)\n"
                    "- comunicados/avisos oficiais da coordenacao (ex: aviso sobre "
                    "certificados, lista de pendencias) - sao informativos, nao reclamacoes\n\n"
                    "Exemplos que DEVEM ser marcados:\n"
                    "- 'O aplicativo caiu de novo, nao consigo cadastrar ninguem'\n"
                    "- 'Ja fizemos o cadastro mas so aparecem 44 familias, sumiram os outros'\n"
                    "- 'Nao conseguimos vincular a familia para a visitadora'\n\n"
                    f"{listagem}"
                ),
            }
        ],
    )
    tool_call = response.choices[0].message.tool_calls[0]
    return json.loads(tool_call.function.arguments).get("problemas", [])


def main(model=None):
    model = model or config.GROQ_MODEL
    groq_client = Groq(api_key=config.GROQ_API_KEY) if config.GROQ_API_KEY else None
    if not groq_client:
        print("GROQ_API_KEY nao definida - nada a fazer.")
        return

    with get_conn() as conn:
        descartadas = run_prefilter(conn)
        if descartadas:
            print(f"Pre-filtro: {descartadas} mensagem(ns) descartada(s) sem custo de API.")

        pending = _fetch_pending(conn)
        if not pending:
            print("Nenhuma mensagem de grupo pendente de analise.")
            return

        print(f"Modelo: {model}")
        total_batches = 0
        total_issues = 0
        failed_batches = 0
        for conv_id, rows in _batches_by_conversation(pending):
            total_batches += 1
            try:
                problemas = classify_batch(groq_client, rows, model)
            except Exception as exc:
                failed_batches += 1
                print(f"  Groq falhou em lote de '{conv_id}' - deixado pendente para nova tentativa: {exc}")
                continue  # nao marca analyzed_at - fica pendente pra proxima execucao

            flagged = {}
            for p in problemas:
                try:
                    idx = int(p["indice"])
                except (KeyError, TypeError, ValueError):
                    continue
                if 0 <= idx < len(rows):
                    flagged[idx] = p

            for i, row in enumerate(rows):
                p = flagged.get(i)
                categoria = p["categoria"] if p else None
                if categoria and categoria not in CATEGORIAS:
                    categoria = "outro"
                conn.execute(
                    """UPDATE group_messages
                       SET is_issue = ?, issue_categoria = ?, issue_tema = ?, analyzed_at = datetime('now')
                       WHERE id = ?""",
                    (
                        1 if p else 0,
                        categoria,
                        p.get("tema") if p else None,
                        row["id"],
                    ),
                )
            conn.commit()
            total_issues += len(flagged)
            print(f"[{conv_id}] lote de {len(rows)} mensagens -> {len(flagged)} problema(s) encontrados")

        print(
            f"Concluido: {total_batches - failed_batches} lote(s) ok, {failed_batches} lote(s) "
            f"pendente(s) (retry), {total_issues} mensagem(ns) marcadas como reclamacao/problema."
        )


if __name__ == "__main__":
    main(model=sys.argv[1] if len(sys.argv) > 1 else None)
