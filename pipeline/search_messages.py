"""Busca semantica local nas group_messages, via similaridade de cosseno
sobre os vetores TF-IDF ja indexados (pipeline/embeddings.py). Sem API.

Uso:
    python pipeline/search_messages.py "aplicativo travando" --top 10
    python pipeline/search_messages.py "cpf errado" --only-issues
"""
import argparse
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from pipeline.db import get_conn
from pipeline.embeddings import load_all_vectors, load_model, model_exists, vectorize


def search(conn, query, top=10, only_issues=False):
    if not model_exists():
        raise SystemExit(
            "Nenhum indice encontrado. Rode `python pipeline/embeddings.py` primeiro."
        )
    vocab, idf = load_model()
    ids, matrix = load_all_vectors(conn)
    if not ids:
        raise SystemExit("Indice vazio. Rode `python pipeline/embeddings.py` primeiro.")

    query_vec = vectorize(query, vocab, idf)
    scores = matrix @ query_vec

    order = np.argsort(-scores)
    results = []
    for i in order:
        if len(results) >= top:
            break
        score = float(scores[i])
        if score <= 0:
            break
        mid = ids[i]
        row = conn.execute(
            "SELECT area, conversation_id, timestamp, sender, content, is_issue "
            "FROM group_messages WHERE id = ?",
            (mid,),
        ).fetchone()
        if row is None:
            continue
        if only_issues and row["is_issue"] != 1:
            continue
        results.append((score, mid, row))
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", help="Texto da busca")
    parser.add_argument("--top", type=int, default=10)
    parser.add_argument("--only-issues", action="store_true", help="So mensagens marcadas como problema")
    args = parser.parse_args()

    with get_conn() as conn:
        results = search(conn, args.query, top=args.top, only_issues=args.only_issues)

    if not results:
        print("Nenhum resultado com similaridade > 0.")
        return

    for score, mid, row in results:
        flag = "PROBLEMA" if row["is_issue"] == 1 else ("-" if row["is_issue"] == 0 else "?")
        snippet = row["content"].replace("\n", " ")[:100]
        print(f"[{score:.3f}] id={mid} {row['timestamp']} ({flag}) {row['sender']}: {snippet}")


if __name__ == "__main__":
    main()
