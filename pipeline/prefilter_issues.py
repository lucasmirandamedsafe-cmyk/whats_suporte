import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from pipeline.db import get_conn
from pipeline.embeddings import load_model, model_exists, vectorize

# Vizinhos considerados no voto semantico, piso de similaridade para um vizinho
# contar, e fracao minima desses vizinhos que precisa ser nao-problema para
# descartar. Conservador de proposito: preferimos deixar passar candidato
# duvidoso pra classificacao profunda a descartar um problema real.
_KNN_K = 8
_KNN_SIM_FLOOR = 0.3
_KNN_MAJORITY = 0.9
_KNN_MIN_NEIGHBORS = 5

# Padroes de mensagens que sabemos com confianca NAO serem reclamacao/erro:
# boilerplate do WhatsApp, saudacoes/agradecimentos isolados, links soltos e
# confirmacoes positivas. Qualquer coisa que nao bater aqui continua pendente
# para a classificacao mais profunda (Groq ou revisao manual) - o filtro so
# descarta o que e obvio, para nao arriscar falso negativo.
_DISCARD_PATTERNS = [
    r"entrou usando o link do grupo",
    r"^voce (adicionou|removeu)",
    r"^.+ (adicionou|removeu) .+",
    r"mensagem apagada",
    r"^cartao do contato omitido$",
    r"^figurinha omitida$",
    r"^imagem ocultada$",
    r"^video omitido$",
    r"^audio ocultado$",
    r"^documento omitido$",
    r"^gif omitido$",
    r"^(bom dia|boa tarde|boa noite|oie?|ola)[!.\s]*$",
    r"^(ok|certo|obrigad[ao]|de nada|sim|show|beleza)[!.\s]*$",
    r"^https?://\S+$",
    r"^(consegui|deu certo|funcionou)[!.\s]*$",
]
_DISCARD_RE = re.compile("|".join(f"(?:{p})" for p in _DISCARD_PATTERNS), re.IGNORECASE)


def _normalize(text):
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode("ascii")
    return text.strip().lower()


def is_confident_non_issue(content: str) -> bool:
    return bool(_DISCARD_RE.search(_normalize(content)))


def _semantic_discard_ids(conn, rows):
    """Segunda passada: para quem sobrou do regex, compara por similaridade
    semantica (TF-IDF) contra as mensagens ja classificadas. So descarta quando
    ha vizinhos suficientes, todos com boa similaridade, e esmagadora maioria
    ja rotulada como nao-problema. Sem indice ainda gerado, nao faz nada."""
    if not rows or not model_exists():
        return set()

    labeled = conn.execute(
        """SELECT g.id AS id, e.vector AS vector, g.is_issue AS is_issue
           FROM group_messages g JOIN message_embeddings e ON e.message_id = g.id
           WHERE g.is_media = 0 AND g.analyzed_at IS NOT NULL"""
    ).fetchall()
    if len(labeled) < _KNN_MIN_NEIGHBORS:
        return set()

    labels = np.array([r["is_issue"] for r in labeled], dtype=np.int8)
    matrix = np.stack([np.frombuffer(r["vector"], dtype=np.float32) for r in labeled])

    vocab, idf = load_model()
    cached = {
        r["message_id"]: np.frombuffer(r["vector"], dtype=np.float32)
        for r in conn.execute("SELECT message_id, vector FROM message_embeddings").fetchall()
    }

    discard_ids = set()
    for row in rows:
        vec = cached.get(row["id"])
        if vec is None:
            vec = vectorize(row["content"], vocab, idf)
        sims = matrix @ vec
        top_idx = np.argsort(-sims)[:_KNN_K]
        top_sims = sims[top_idx]
        neighbors = top_idx[top_sims >= _KNN_SIM_FLOOR]
        if len(neighbors) < _KNN_MIN_NEIGHBORS:
            continue
        non_issue_frac = float((labels[neighbors] == 0).mean())
        if non_issue_frac >= _KNN_MAJORITY:
            discard_ids.add(row["id"])
    return discard_ids


def run(conn) -> int:
    """Marca is_issue=0 direto para mensagens obviamente nao-problema, sem gastar
    chamada de LLM nelas: primeiro por regex (boilerplate/saudacao/link), depois
    por similaridade semantica contra o que ja foi classificado (se houver indice).
    Retorna quantas foram descartadas nessa passada."""
    rows = conn.execute(
        "SELECT id, content FROM group_messages WHERE is_media = 0 AND analyzed_at IS NULL"
    ).fetchall()

    discarded = 0
    remaining = []
    for row in rows:
        if is_confident_non_issue(row["content"]):
            conn.execute(
                """UPDATE group_messages
                   SET is_issue = 0, issue_categoria = NULL, issue_tema = NULL, issue_tipo = NULL,
                       analyzed_at = datetime('now')
                   WHERE id = ?""",
                (row["id"],),
            )
            discarded += 1
        else:
            remaining.append(row)

    semantic_ids = _semantic_discard_ids(conn, remaining)
    for mid in semantic_ids:
        conn.execute(
            """UPDATE group_messages
               SET is_issue = 0, issue_categoria = NULL, issue_tema = NULL, issue_tipo = NULL,
                   analyzed_at = datetime('now')
               WHERE id = ?""",
            (mid,),
        )
    discarded += len(semantic_ids)

    conn.commit()
    return discarded


def main():
    with get_conn() as conn:
        discarded = run(conn)
        restante = conn.execute(
            "SELECT COUNT(*) c FROM group_messages WHERE is_media = 0 AND analyzed_at IS NULL"
        ).fetchone()["c"]
    print(f"Pre-filtro: {discarded} mensagem(ns) descartada(s) sem custo de API, {restante} candidata(s) restante(s).")


if __name__ == "__main__":
    main()
