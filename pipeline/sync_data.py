"""Sincronizacao incremental de dados brutos (raw/) pro banco.

Uso: python pipeline/sync_data.py

Roda toda vez que voce adicionar/atualizar exports do WhatsApp em raw/ e quer
alimentar o banco sem reprocessar do zero. Ele:

  1. Descobre as pastas automaticamente (nao tem lista fixa de areas):
     - raw/<area>/          -> grupos (vira group_messages)
     - raw/suporte/<area>/  -> suporte 1:1 (vira messages/sessions)
     - raw/suporte/*.txt solto (sem subpasta) -> suporte sem area
     Pastas vazias (ex: raw/suporte/suporte_educacao ainda sem conversas) sao
     silenciosamente ignoradas ate terem arquivo dentro - nao precisa editar
     este script quando elas ganharem conteudo.

  2. Extrai .zip -> .txt (sobrescreve o .txt sempre que o zip mudar).

  3. Para cada .txt, compara um hash do conteudo com o que ja foi sincronizado
     (tabela ingested_files). Sem mudanca -> pula. Com mudanca -> descobre
     quantas mensagens dessa conversa ja estao no banco e insere so as que
     vem DEPOIS dessa posicao (assume que export do WhatsApp e sempre uma
     re-exportacao completa e cronologica - so cresce no final). Mensagens
     antigas ja classificadas NUNCA sao tocadas nem reclassificadas.

  4. Nao chama Groq nem Gemini (pra nao gastar cota sem voce saber). So faz
     o que e local/gratis: pre-filtro heuristico+semantico e reindexacao TF-IDF
     pros grupos, e recalculo de sessoes/tempo de resposta pro suporte. No
     final, imprime um lembrete do que rodar manualmente pra classificar o
     que entrou de novo.
"""
import hashlib
import sys
import zipfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from pipeline import classify_suporte_local, parse, prefilter_issues
from pipeline.db import get_conn, init_db


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _extract_zips(folder: Path):
    for zip_path in sorted(folder.glob("*.zip")):
        try:
            with zipfile.ZipFile(zip_path) as z:
                names = [n for n in z.namelist() if n.endswith(".txt")]
                if not names:
                    continue
                with z.open(names[0]) as f:
                    raw = f.read().decode("utf-8-sig")
        except zipfile.BadZipFile:
            print(f"  aviso: {zip_path.name} nao e um zip valido, ignorando")
            continue
        zip_path.with_suffix(".txt").write_text(raw, encoding="utf-8")


def _discover_targets():
    """Retorna lista de (txt_path, kind, area) - kind e 'grupo' ou 'suporte'."""
    targets = []
    raw_root = config.RAW_DIR.parent  # raw/ - suporte/ e as pastas de grupo (assistencia, saude, ...) sao irmas aqui

    for area_dir in sorted(p for p in raw_root.glob("*") if p.is_dir() and p.name != "suporte"):
        _extract_zips(area_dir)
        for txt in sorted(area_dir.glob("*.txt")):
            targets.append((txt, "grupo", area_dir.name))

    _extract_zips(config.RAW_DIR)
    for txt in sorted(config.RAW_DIR.glob("*.txt")):
        targets.append((txt, "suporte", None))

    for sub_dir in sorted(p for p in config.RAW_DIR.glob("*") if p.is_dir()):
        _extract_zips(sub_dir)
        area = sub_dir.name.removeprefix("suporte_") if sub_dir.name.startswith("suporte_") else sub_dir.name
        for txt in sorted(sub_dir.glob("*.txt")):
            targets.append((txt, "suporte", area))

    return targets


def _get_ingested(conn, rel_path):
    return conn.execute("SELECT * FROM ingested_files WHERE path = ?", (rel_path,)).fetchone()


def _upsert_ingested(conn, rel_path, kind, area, conversation_id, content_hash, message_count):
    conn.execute(
        """INSERT INTO ingested_files (path, kind, area, conversation_id, content_hash, message_count, last_synced_at)
           VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
           ON CONFLICT(path) DO UPDATE SET
               content_hash = excluded.content_hash,
               message_count = excluded.message_count,
               last_synced_at = excluded.last_synced_at""",
        (rel_path, kind, area, conversation_id, content_hash, message_count),
    )


def _sync_grupo(conn, path: Path, area: str) -> int:
    conversation_id = path.stem
    existing = conn.execute(
        "SELECT COUNT(*) c FROM group_messages WHERE conversation_id = ?", (conversation_id,)
    ).fetchone()["c"]

    messages = parse.parse_raw_lines(path)
    novas = messages[existing:]
    if not novas:
        return 0

    conn.executemany(
        """INSERT INTO group_messages (area, conversation_id, timestamp, sender, is_media, content)
           VALUES (?, ?, ?, ?, ?, ?)""",
        [
            (area, conversation_id, m["timestamp"].isoformat(), m["sender"], int(m["is_media"]), m["content"])
            for m in novas
        ],
    )
    return len(novas)


def _sync_suporte(conn, path: Path, area: str, sessoes_tocadas: set) -> int:
    conversation_id = path.stem
    existing = conn.execute(
        "SELECT COUNT(*) c FROM messages WHERE conversation_id = ?", (conversation_id,)
    ).fetchone()["c"]

    todas = parse.parse_file(path, area=area)
    novas = todas[existing:]
    if not novas:
        return 0

    parse.assign_sessions(todas)  # atribui session_id em todas (mutacao in-place), inclusive nas novas
    parse.save_messages(conn, novas)
    sessoes_tocadas.update(m["session_id"] for m in novas)
    return len(novas)


def main():
    init_db()
    if not config.SUPPORT_SENDER_NAMES:
        print("Aviso: config.SUPPORT_SENDER_NAMES vazio - mensagens de suporte nao serao identificadas como tal.")

    targets = _discover_targets()
    if not targets:
        print("Nenhum arquivo encontrado em raw/.")
        return

    grupo_mudou = False
    suporte_mudou = False
    sessoes_tocadas = set()
    resumo = []

    raw_root = config.RAW_DIR.parent

    with get_conn() as conn:
        for path, kind, area in targets:
            rel_path = str(path.relative_to(raw_root))
            content = path.read_text(encoding="utf-8")
            content_hash = _hash_text(content)
            ingested = _get_ingested(conn, rel_path)

            if ingested and ingested["content_hash"] == content_hash:
                resumo.append(f"  [sem mudanca] {rel_path}")
                continue

            if kind == "grupo":
                n = _sync_grupo(conn, path, area)
                total = conn.execute(
                    "SELECT COUNT(*) c FROM group_messages WHERE conversation_id = ?", (path.stem,)
                ).fetchone()["c"]
                if n:
                    grupo_mudou = True
            else:
                n = _sync_suporte(conn, path, area, sessoes_tocadas)
                total = conn.execute(
                    "SELECT COUNT(*) c FROM messages WHERE conversation_id = ?", (path.stem,)
                ).fetchone()["c"]
                if n:
                    suporte_mudou = True

            _upsert_ingested(conn, rel_path, kind, area, path.stem, content_hash, total)
            status = f"+{n} mensagem(ns) nova(s)" if n else "sem mensagem nova (so mudou algo irrelevante no arquivo)"
            resumo.append(f"  [{kind}/{area or '-'}] {rel_path}: {status}")

        if suporte_mudou:
            parse.build_sessions(conn)
            if sessoes_tocadas:
                conn.executemany(
                    """UPDATE sessions SET analyzed_at = NULL, categoria = NULL, tema = NULL,
                           sentimento = NULL, resumo = NULL WHERE session_id = ?""",
                    [(sid,) for sid in sessoes_tocadas],
                )
            n_reclamacoes = classify_suporte_local.run(conn)
            print(f"Classificacao local (suporte): {n_reclamacoes} mensagem(ns) nova(s) marcada(s) como reclamacao/erro.")

        conn.commit()

        if grupo_mudou:
            descartadas = prefilter_issues.run(conn)
            print(f"Pre-filtro (grupos): {descartadas} mensagem(ns) descartada(s) sem custo de API.")

    print("\n".join(resumo))

    if grupo_mudou:
        from pipeline import embeddings

        embeddings.reindex()

    print()
    if not grupo_mudou and not suporte_mudou:
        print("Nada novo pra sincronizar.")
    else:
        print("Sincronizacao concluida. Passos manuais que ainda faltam (custam API, por isso nao rodam sozinhos):")
        if grupo_mudou:
            print("  - python pipeline/classify_issues.py   (Groq: is_issue/categoria/tema das mensagens novas)")
            print("  - python pipeline/classify_tipo_erro.py (Groq: tipo dos problemas novos)")
        if suporte_mudou:
            print(f"  - python pipeline/enrich_ai.py          (Groq+Gemini: {len(sessoes_tocadas)} atendimento(s) pra reclassificar)")


if __name__ == "__main__":
    main()
