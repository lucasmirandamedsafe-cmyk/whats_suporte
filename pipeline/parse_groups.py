import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from pipeline.db import get_conn, init_db
from pipeline.parse import parse_raw_lines

AREAS = ["saude", "educacao", "assistencia"]


def area_dir(area):
    return config.RAW_DIR.parent / area


def parse_area(area):
    messages = []
    for path in sorted(area_dir(area).glob("*.txt")):
        conversation_id = path.stem
        for m in parse_raw_lines(path):
            messages.append({**m, "area": area, "conversation_id": conversation_id})
    return messages


def save_messages(conn, messages):
    conn.executemany(
        """INSERT INTO group_messages
               (area, conversation_id, timestamp, sender, is_media, content)
           VALUES
               (:area, :conversation_id, :timestamp, :sender, :is_media, :content)""",
        [
            {
                **m,
                "timestamp": m["timestamp"].isoformat(),
                "is_media": int(m["is_media"]),
            }
            for m in messages
        ],
    )


def main():
    init_db()
    with get_conn() as conn:
        conn.execute("DELETE FROM group_messages")
        for area in AREAS:
            txt_files = sorted(area_dir(area).glob("*.txt"))
            if not txt_files:
                print(f"{area}: nenhum .txt encontrado em {area_dir(area)}")
                continue
            messages = parse_area(area)
            save_messages(conn, messages)
            print(f"{area}: {len(txt_files)} arquivo(s), {len(messages)} mensagens")
        conn.commit()
    print("Parsing de grupos concluido.")


if __name__ == "__main__":
    main()
