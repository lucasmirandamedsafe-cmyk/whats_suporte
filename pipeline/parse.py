import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from pipeline.db import get_conn, init_db

MEDIA_MARKERS = [
    "mídia oculta", "midia oculta", "media omitted", "image omitted",
    "audio omitted", "video omitted", "sticker omitted", "documento omitido",
    "gif omitted", "<attached:",
]

# Suporta os dois formatos mais comuns de export do WhatsApp (Android e iOS).
# Não cobre variações locais com hora em formato 12h (AM/PM) - ajuste aqui se necessário.
LINE_PATTERNS = [
    re.compile(r"^(?P<date>\d{1,2}/\d{1,2}/\d{2,4}),?\s(?P<time>\d{1,2}:\d{2}(?::\d{2})?)\s-\s(?P<rest>.*)$"),
    re.compile(r"^\[(?P<date>\d{1,2}/\d{1,2}/\d{2,4}),\s(?P<time>\d{1,2}:\d{2}(?::\d{2})?)\]\s(?P<rest>.*)$"),
]

SENDER_CONTENT_RE = re.compile(r"^([^:]{1,60}?):\s(.*)$")


def _parse_datetime(date_str, time_str):
    for date_fmt in ("%d/%m/%Y", "%d/%m/%y"):
        for time_fmt in ("%H:%M:%S", "%H:%M"):
            try:
                return datetime.strptime(f"{date_str} {time_str}", f"{date_fmt} {time_fmt}")
            except ValueError:
                continue
    raise ValueError(f"Timestamp não reconhecido: {date_str} {time_str}")


def _split_sender_content(rest):
    match = SENDER_CONTENT_RE.match(rest)
    if not match:
        return None, rest
    sender = match.group(1).strip().replace("\n", " ")
    return sender, match.group(2).strip()


def _is_media(content):
    lowered = content.lower()
    return any(marker in lowered for marker in MEDIA_MARKERS)


def _is_support(sender):
    if not sender:
        return False
    sender_lower = sender.lower()
    return any(name.lower() in sender_lower for name in config.SUPPORT_SENDER_NAMES)


_MAX_PENDING_SENDER_LINES = 5


def parse_raw_lines(path: Path):
    """Le um export do WhatsApp (grupo ou 1:1) e devolve as mensagens reais,
    sem conversation_id/is_support - mensagens de sistema (criptografia,
    entrou/saiu do grupo etc.) ja vem filtradas."""
    messages = []
    current = None
    pending = None  # {"timestamp": ..., "buffer": [str, ...]} enquanto o nome do
    # remetente vem quebrado em mais de uma linha (contato/grupo com nome
    # multi-linha - o ':' que separa remetente de conteudo cai numa linha seguinte)

    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip("‎‏").rstrip()
        if not line:
            continue

        matched = None
        for pattern in LINE_PATTERNS:
            m = pattern.match(line)
            if m:
                matched = m
                break

        if matched:
            pending = None
            timestamp = _parse_datetime(matched.group("date"), matched.group("time"))
            sender, content = _split_sender_content(matched.group("rest"))
            if sender is None:
                pending = {"timestamp": timestamp, "buffer": [matched.group("rest")]}
                current = None
                continue
            current = {
                "timestamp": timestamp,
                "sender": sender,
                "is_media": _is_media(content),
                "content": content,
            }
            messages.append(current)
        elif pending is not None:
            pending["buffer"].append(line)
            sender, content = _split_sender_content("\n".join(pending["buffer"]))
            if sender is not None:
                current = {
                    "timestamp": pending["timestamp"],
                    "sender": sender,
                    "is_media": _is_media(content),
                    "content": content,
                }
                messages.append(current)
                pending = None
            elif len(pending["buffer"]) >= _MAX_PENDING_SENDER_LINES:
                pending = None
        elif current is not None:
            current["content"] += "\n" + line

    return messages


def parse_file(path: Path, area: str = None):
    conversation_id = path.stem
    messages = parse_raw_lines(path)
    for m in messages:
        m["conversation_id"] = conversation_id
        m["is_support"] = _is_support(m["sender"])
        m["area"] = area
    return messages


def assign_sessions(messages):
    gap = timedelta(hours=config.SESSION_GAP_HOURS)
    messages = sorted(messages, key=lambda m: m["timestamp"])
    session_id = None
    last_ts = None
    for msg in messages:
        if last_ts is None or (msg["timestamp"] - last_ts) > gap:
            session_id = f"{msg['conversation_id']}__{msg['timestamp'].isoformat()}"
        msg["session_id"] = session_id
        last_ts = msg["timestamp"]
    return messages


def save_messages(conn, messages):
    conn.executemany(
        """INSERT INTO messages
               (area, conversation_id, session_id, timestamp, sender, is_support, is_media, content)
           VALUES
               (:area, :conversation_id, :session_id, :timestamp, :sender, :is_support, :is_media, :content)""",
        [
            {
                **m,
                "timestamp": m["timestamp"].isoformat(),
                "is_support": int(m["is_support"]),
                "is_media": int(m["is_media"]),
            }
            for m in messages
        ],
    )


def build_sessions(conn):
    rows = conn.execute(
        "SELECT session_id, area, conversation_id, timestamp, is_support FROM messages ORDER BY session_id, timestamp"
    ).fetchall()

    sessions = {}
    for row in rows:
        s = sessions.setdefault(
            row["session_id"],
            {
                "session_id": row["session_id"],
                "area": row["area"],
                "conversation_id": row["conversation_id"],
                "started_at": row["timestamp"],
                "ended_at": row["timestamp"],
                "message_count": 0,
                "first_customer_ts": None,
                "first_response_seconds": None,
            },
        )
        s["ended_at"] = row["timestamp"]
        s["message_count"] += 1
        if not row["is_support"] and s["first_customer_ts"] is None:
            s["first_customer_ts"] = row["timestamp"]
        if row["is_support"] and s["first_customer_ts"] is not None and s["first_response_seconds"] is None:
            delta = datetime.fromisoformat(row["timestamp"]) - datetime.fromisoformat(s["first_customer_ts"])
            s["first_response_seconds"] = delta.total_seconds()

    for s in sessions.values():
        conn.execute(
            """INSERT INTO sessions
                   (session_id, area, conversation_id, started_at, ended_at, message_count, first_response_seconds)
               VALUES
                   (:session_id, :area, :conversation_id, :started_at, :ended_at, :message_count, :first_response_seconds)
               ON CONFLICT(session_id) DO UPDATE SET
                   ended_at = excluded.ended_at,
                   message_count = excluded.message_count,
                   first_response_seconds = excluded.first_response_seconds""",
            s,
        )


def _area_for(path: Path):
    """Deriva a area a partir da subpasta (raw/suporte/suporte_assistencia/x.txt ->
    'assistencia'). Arquivos soltos direto em raw/suporte/ ficam sem area (None)."""
    if path.parent == config.RAW_DIR:
        return None
    name = path.parent.name
    return name.removeprefix("suporte_") if name.startswith("suporte_") else name


def main():
    init_db()
    txt_files = sorted(config.RAW_DIR.rglob("*.txt"))
    if not txt_files:
        print(f"Nenhum .txt encontrado em {config.RAW_DIR} (nem em subpastas). Coloque os exports do WhatsApp lá.")
        return

    if not config.SUPPORT_SENDER_NAMES:
        print("Aviso: config.SUPPORT_SENDER_NAMES está vazio - todas as mensagens serão tratadas como do cliente.")
        print("Edite config.py com o(s) nome(s) que identificam o suporte nos exports.")

    with get_conn() as conn:
        conn.execute("DELETE FROM messages")
        conn.execute("DELETE FROM sessions")
        for path in txt_files:
            area = _area_for(path)
            messages = assign_sessions(parse_file(path, area=area))
            save_messages(conn, messages)
            print(f"[{area or '-'}] {path.name}: {len(messages)} mensagens")
        build_sessions(conn)
        conn.commit()

    print("Parsing concluído.")


if __name__ == "__main__":
    main()
