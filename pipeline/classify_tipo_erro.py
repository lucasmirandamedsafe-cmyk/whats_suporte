import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from groq import Groq

import config
from pipeline.db import get_conn, init_db

BATCH_SIZE = 20

TIPOS_ERRO = [
    "cadastro_dados",
    "acesso_login",
    "visitas_acompanhamento",
    "cursos_certificados",
    "processo_administrativo",
    "instabilidade_plataforma",
    "outro",
]

DESCRICAO_TIPOS = (
    "cadastro_dados: erro/dado errado em cadastro (CPF, CNPJ, familia, membro, equipe)\n"
    "acesso_login: nao consegue entrar, senha, tela nao aparece, conexao\n"
    "visitas_acompanhamento: visita, formulario, acompanhamento de criancas/gestantes\n"
    "cursos_certificados: cursos, certificados, capacitacao\n"
    "processo_administrativo: vinculacao de CNPJ/CRAS, aprovacao, exclusao de usuario, requisitos, orientacao\n"
    "instabilidade_plataforma: plataforma/app nao funciona, erro de atualizacao/visualizacao/localizacao, erro desconhecido\n"
    "outro: qualquer coisa que nao se encaixe bem nas anteriores"
)

TOOL = {
    "type": "function",
    "function": {
        "name": "classificar_tipo_erro",
        "description": "Classifica o tipo de erro/reclamacao de cada mensagem com base no tema resumido.",
        "parameters": {
            "type": "object",
            "properties": {
                "classificacoes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "indice": {"type": ["integer", "string"], "description": "indice do tema na lista"},
                            "tipo": {"type": "string", "description": f"uma de: {', '.join(TIPOS_ERRO)}"},
                        },
                    },
                }
            },
            "required": ["classificacoes"],
        },
    },
}


def _fetch_pending(conn):
    return conn.execute(
        "SELECT id, issue_tema, content FROM group_messages "
        "WHERE is_issue = 1 AND issue_tipo IS NULL ORDER BY id"
    ).fetchall()


def _batches(rows):
    for i in range(0, len(rows), BATCH_SIZE):
        yield rows[i : i + BATCH_SIZE]


def classify_batch(client, model, rows):
    listagem = "\n".join(f"{i}. {r['issue_tema'] or r['content'][:80]}" for i, r in enumerate(rows))
    response = client.chat.completions.create(
        model=model,
        max_tokens=3000,
        tools=[TOOL],
        tool_choice={"type": "function", "function": {"name": "classificar_tipo_erro"}},
        messages=[
            {
                "role": "user",
                "content": (
                    "Classifique cada tema de reclamacao/erro abaixo em um dos tipos:\n\n"
                    f"{DESCRICAO_TIPOS}\n\nTemas:\n{listagem}"
                ),
            }
        ],
    )
    tool_call = response.choices[0].message.tool_calls[0]
    return json.loads(tool_call.function.arguments).get("classificacoes", [])


def main(model=None):
    model = model or config.GROQ_MODEL
    groq_client = Groq(api_key=config.GROQ_API_KEY) if config.GROQ_API_KEY else None
    if not groq_client:
        print("GROQ_API_KEY nao definida - nada a fazer.")
        return

    init_db()
    with get_conn() as conn:
        pending = _fetch_pending(conn)
        if not pending:
            print("Nenhuma mensagem pendente de classificacao de tipo de erro.")
            return

        print(f"Modelo: {model} - {len(pending)} mensagem(ns) pendente(s)")
        for rows in _batches(pending):
            try:
                classificacoes = classify_batch(groq_client, model, rows)
            except Exception as exc:
                print(f"  Groq falhou em lote - deixado pendente para nova tentativa: {exc}")
                continue

            tipos = {}
            for c in classificacoes:
                c = {str(k).strip().lower(): v for k, v in c.items()} if isinstance(c, dict) else {}
                idx_raw = c.get("indice", c.get("index"))
                try:
                    idx = int(idx_raw)
                except (TypeError, ValueError):
                    continue
                if 0 <= idx < len(rows):
                    tipo = c.get("tipo", c.get("type"))
                    tipos[idx] = tipo if tipo in TIPOS_ERRO else "outro"

            for i, row in enumerate(rows):
                tipo = tipos.get(i, "outro")
                conn.execute("UPDATE group_messages SET issue_tipo = ? WHERE id = ?", (tipo, row["id"]))
            conn.commit()
            print(f"lote de {len(rows)} mensagens classificado")

    print("Concluido.")


if __name__ == "__main__":
    main(model=sys.argv[1] if len(sys.argv) > 1 else None)
