import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google import genai
from groq import Groq

import config
from pipeline.db import get_conn

CATEGORIAS = ["duvida", "reclamacao", "elogio", "outro"]
SENTIMENTOS = ["positivo", "neutro", "negativo"]

# Groq classifica (barato/rápido) - categoria, tema e sentimento
GROQ_TOOL = {
    "type": "function",
    "function": {
        "name": "classificar_atendimento",
        "description": "Classifica um atendimento de suporte via WhatsApp.",
        "parameters": {
            "type": "object",
            "properties": {
                "categoria": {"type": "string", "enum": CATEGORIAS},
                "tema": {
                    "type": "string",
                    "description": (
                        "Tema principal do atendimento em 2-4 palavras, ex: "
                        "'cobranca indevida', 'duvida sobre entrega', 'bug no app'"
                    ),
                },
                "sentimento": {"type": "string", "enum": SENTIMENTOS},
            },
            "required": ["categoria", "tema", "sentimento"],
        },
    },
}


def _transcript(conn, session_id):
    rows = conn.execute(
        "SELECT is_support, content FROM messages WHERE session_id = ? AND is_media = 0 ORDER BY timestamp",
        (session_id,),
    ).fetchall()
    linhas = [f"{'Suporte' if row['is_support'] else 'Cliente'}: {row['content']}" for row in rows]
    return "\n".join(linhas)


def classify_with_groq(client, transcript):
    response = client.chat.completions.create(
        model=config.GROQ_MODEL,
        max_tokens=300,
        tools=[GROQ_TOOL],
        tool_choice={"type": "function", "function": {"name": "classificar_atendimento"}},
        messages=[
            {
                "role": "user",
                "content": (
                    "Classifique o atendimento de suporte abaixo (conversa entre Cliente e "
                    f"Suporte via WhatsApp).\n\n{transcript}"
                ),
            }
        ],
    )
    tool_call = response.choices[0].message.tool_calls[0]
    return json.loads(tool_call.function.arguments)


def summarize_with_gemini(client, transcript):
    response = client.models.generate_content(
        model=config.GEMINI_MODEL,
        contents=(
            "Resuma em até 2 frases, em português, o atendimento de suporte via WhatsApp "
            f"abaixo (conversa entre Cliente e Suporte):\n\n{transcript}"
        ),
    )
    return response.text.strip()


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    groq_client = Groq(api_key=config.GROQ_API_KEY) if config.GROQ_API_KEY else None
    if not groq_client:
        print("GROQ_API_KEY não definida - categoria/tema/sentimento serão pulados.")

    gemini_client = genai.Client(api_key=config.GEMINI_API_KEY) if config.GEMINI_API_KEY else None
    if not gemini_client:
        print("GEMINI_API_KEY não definida - resumo será pulado.")

    if not groq_client and not gemini_client:
        print("Nenhuma API configurada. Defina GROQ_API_KEY e/ou GEMINI_API_KEY no .env.")
        return

    with get_conn() as conn:
        pending = conn.execute("SELECT session_id FROM sessions WHERE analyzed_at IS NULL").fetchall()

        if not pending:
            print("Nenhuma sessão pendente de análise.")
            return

        for i, row in enumerate(pending, start=1):
            session_id = row["session_id"]
            transcript = _transcript(conn, session_id)
            if not transcript.strip():
                continue

            categoria = tema = sentimento = resumo = None

            if groq_client:
                try:
                    classificacao = classify_with_groq(groq_client, transcript)
                    categoria = classificacao["categoria"]
                    tema = classificacao["tema"]
                    sentimento = classificacao["sentimento"]
                except Exception as exc:
                    print(f"[{i}/{len(pending)}] Groq falhou em {session_id}: {exc}")

            if gemini_client:
                try:
                    resumo = summarize_with_gemini(gemini_client, transcript)
                except Exception as exc:
                    print(f"[{i}/{len(pending)}] Gemini falhou em {session_id}: {exc}")

            conn.execute(
                """UPDATE sessions
                   SET categoria = ?, tema = ?, sentimento = ?, resumo = ?, analyzed_at = datetime('now')
                   WHERE session_id = ?""",
                (categoria, tema, sentimento, resumo, session_id),
            )
            conn.commit()
            print(f"[{i}/{len(pending)}] {session_id}: {categoria}/{tema}/{sentimento}")


if __name__ == "__main__":
    main()
