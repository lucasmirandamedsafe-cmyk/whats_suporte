"""Indexador semantico local (TF-IDF) das group_messages - sem depender de
nenhuma API externa. Usado para busca por similaridade (search_messages.py),
dedup de incidentes por conteudo parecido e um pre-filtro mais esperto.

Reindexar sempre recalcula vocabulario/IDF a partir do corpus atual inteiro
(rapido o bastante nessa escala - milhares de mensagens curtas) e reescreve
todos os vetores, evitando bugs de vocabulario desatualizado.
"""
import json
import math
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

import config
from pipeline.db import get_conn, init_db

MODEL_NAME = "tfidf-v1"
MODEL_PATH = config.BASE_DIR / "data" / "tfidf_model.json"
MAX_FEATURES = 4000
MIN_DF = 2

_STOPWORDS = {
    "a", "o", "e", "de", "do", "da", "dos", "das", "em", "no", "na", "nos", "nas",
    "um", "uma", "uns", "umas", "para", "por", "com", "sem", "que", "se", "ja",
    "eu", "tu", "ele", "ela", "nos", "voces", "eles", "elas", "sou", "es", "e",
    "foi", "ser", "estar", "esta", "estao", "isso", "essa", "esse", "aquilo",
    "mais", "muito", "ao", "aos", "as", "pra", "pro", "mas", "ou", "tambem",
    "ja", "nao", "sim", "me", "te", "lhe", "meu", "minha", "seu", "sua", "aqui",
    "la", "vou", "vai", "tem", "ter", "so", "ainda", "entao", "como", "quando",
    "onde", "qual", "quais", "porque", "pq", "vc", "vcs", "voce",
}


def _normalize(text):
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode("ascii")
    return text.lower()


def tokenize(text):
    tokens = re.findall(r"[a-z]{2,}", _normalize(text))
    return [t for t in tokens if t not in _STOPWORDS]


def fit_vectorizer(texts):
    doc_freq = Counter()
    tokenized_docs = []
    for text in texts:
        tokens = set(tokenize(text))
        tokenized_docs.append(tokens)
        doc_freq.update(tokens)

    vocab_terms = [term for term, df in doc_freq.items() if df >= MIN_DF]
    vocab_terms.sort(key=lambda t: -doc_freq[t])
    vocab_terms = vocab_terms[:MAX_FEATURES]
    vocab = {term: idx for idx, term in enumerate(vocab_terms)}

    n_docs = len(texts)
    idf = np.zeros(len(vocab), dtype=np.float32)
    for term, idx in vocab.items():
        idf[idx] = math.log((1 + n_docs) / (1 + doc_freq[term])) + 1.0
    return vocab, idf


def vectorize(text, vocab, idf):
    counts = Counter(tokenize(text))
    vec = np.zeros(len(vocab), dtype=np.float32)
    for term, count in counts.items():
        idx = vocab.get(term)
        if idx is not None:
            vec[idx] = (1.0 + math.log(count)) * idf[idx]
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec /= norm
    return vec


def cosine_sim(a, b):
    return float(np.dot(a, b))


def save_model(vocab, idf, path=MODEL_PATH):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"model": MODEL_NAME, "vocab": vocab, "idf": idf.tolist()}, f)


def load_model(path=MODEL_PATH):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data["vocab"], np.array(data["idf"], dtype=np.float32)


def model_exists(path=MODEL_PATH):
    return path.exists()


def reindex():
    """Recalcula vocabulario/IDF e todos os vetores a partir do corpus atual."""
    init_db()
    with get_conn() as conn:
        rows = conn.execute("SELECT id, content FROM group_messages WHERE is_media = 0").fetchall()
        if not rows:
            print("Nenhuma mensagem para indexar.")
            return

        texts = [r["content"] for r in rows]
        vocab, idf = fit_vectorizer(texts)
        save_model(vocab, idf)

        conn.execute("DELETE FROM message_embeddings")
        for row in rows:
            vec = vectorize(row["content"], vocab, idf)
            conn.execute(
                "INSERT INTO message_embeddings (message_id, vector, model, created_at) "
                "VALUES (?, ?, ?, datetime('now'))",
                (row["id"], vec.astype(np.float32).tobytes(), MODEL_NAME),
            )
        conn.commit()
        print(f"Indexadas {len(rows)} mensagem(ns) - vocabulario com {len(vocab)} termos.")


def load_all_vectors(conn):
    """Retorna (message_ids: list[int], matrix: np.ndarray [n, dim])."""
    rows = conn.execute("SELECT message_id, vector FROM message_embeddings").fetchall()
    if not rows:
        return [], np.zeros((0, 0), dtype=np.float32)
    ids = [r["message_id"] for r in rows]
    matrix = np.stack([np.frombuffer(r["vector"], dtype=np.float32) for r in rows])
    return ids, matrix


if __name__ == "__main__":
    reindex()
