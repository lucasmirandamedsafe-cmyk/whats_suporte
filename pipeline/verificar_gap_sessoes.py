"""Verifica empiricamente se config.SESSION_GAP_HOURS (gap que separa um
atendimento/sessao do proximo, ver pipeline/parse.py::assign_sessions) esta bem
posicionado, olhando a distribuicao real dos intervalos entre mensagens
consecutivas de uma mesma conversa.

Metodo: para cada conversation_id, ordena as mensagens por timestamp e calcula
o intervalo (em horas) entre uma mensagem e a anterior. Um bom valor de corte
deve cair num "vale" da distribuicao - uma faixa onde poucos ou nenhum gap real
e observado - separando "resposta na mesma conversa corrida" (gaps pequenos,
minutos/poucas horas) de "resposta so no proximo periodo de atendimento" (gaps
grandes, meio dia ou mais). Se o valor de corte caisse no meio de uma faixa
com muitos gaps, ele estaria cortando atendimentos no meio ou juntando
atendimentos distintos.

Ver docs/session-gap-6h-analise.md para o resultado da ultima execucao e a
conclusao (SESSION_GAP_HOURS = 6 cai nesse vale, nao precisou mudar).

Uso: python pipeline/verificar_gap_sessoes.py
"""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd

import config
from pipeline.db import get_conn

PERCENTIS = [50, 75, 80, 85, 90, 92, 95, 97, 98, 99]
LIMIARES_HORAS = [0.0833, 0.25, 0.5, 1, 2, 3, 4, 5, 6, 8, 10, 12, 16, 20, 24, 48]
FAIXA_HISTOGRAMA_HORAS = 30


def calcular_gaps(conn) -> pd.Series:
    df = pd.read_sql_query(
        "SELECT conversation_id, timestamp FROM messages ORDER BY conversation_id, timestamp",
        conn,
        parse_dates=["timestamp"],
    )
    df["prev_ts"] = df.groupby("conversation_id")["timestamp"].shift(1)
    df["gap_horas"] = (df["timestamp"] - df["prev_ts"]).dt.total_seconds() / 3600
    gaps = df["gap_horas"].dropna()
    return gaps[gaps >= 0]


def main():
    with get_conn() as conn:
        gaps = calcular_gaps(conn)

    print(f"SESSION_GAP_HOURS atual: {config.SESSION_GAP_HOURS}h")
    print(f"total de gaps analisados: {len(gaps)}\n")

    print("Percentis (horas):")
    for p in PERCENTIS:
        print(f"  p{p}: {np.percentile(gaps, p):.2f}h")

    print("\n% de gaps <= X horas:")
    for x in LIMIARES_HORAS:
        pct = (gaps <= x).mean() * 100
        marcador = "  <-- gap atual" if x == config.SESSION_GAP_HOURS else ""
        print(f"  <= {x}h: {pct:.2f}%{marcador}")

    print(f"\nDistribuicao de gaps entre 0h e {FAIXA_HISTOGRAMA_HORAS}h (bins de 1h):")
    bins = list(range(0, FAIXA_HISTOGRAMA_HORAS + 1))
    hist, edges = np.histogram(gaps[gaps <= FAIXA_HISTOGRAMA_HORAS], bins=bins)
    for i, h in enumerate(hist):
        marcador = "  <-- gap atual" if edges[i] <= config.SESSION_GAP_HOURS < edges[i + 1] else ""
        print(f"  {edges[i]:>2.0f}-{edges[i+1]:>2.0f}h: {h}{marcador}")


if __name__ == "__main__":
    main()
