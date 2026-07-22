import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd


def load_sessions(conn) -> pd.DataFrame:
    return pd.read_sql_query(
        "SELECT * FROM sessions", conn, parse_dates=["started_at", "ended_at", "analyzed_at"]
    )


def load_customer_messages(conn) -> pd.DataFrame:
    """Mensagens do cliente (nao do suporte) no atendimento 1:1, com a
    classificacao local de reclamacao/erro (pipeline/classify_suporte_local.py)."""
    return pd.read_sql_query(
        "SELECT * FROM messages WHERE is_support = 0 AND is_media = 0",
        conn,
        parse_dates=["timestamp", "analyzed_at"],
    )


def kpis_reclamacao_suporte(df_msgs: pd.DataFrame) -> dict:
    total = len(df_msgs)
    reclamacoes = int((df_msgs["is_issue"] == 1).sum()) if total else 0
    return {
        "total_mensagens_cliente": total,
        "total_reclamacoes": reclamacoes,
        "pct_reclamacoes": round(reclamacoes / total * 100, 1) if total else 0,
    }


def distribuicao_categoria_suporte(df_msgs: pd.DataFrame) -> pd.DataFrame:
    out = df_msgs[df_msgs["is_issue"] == 1]
    return out["issue_categoria"].value_counts().rename_axis("categoria").reset_index(name="mensagens")


def distribuicao_tipo_suporte(df_msgs: pd.DataFrame) -> pd.DataFrame:
    out = df_msgs[df_msgs["is_issue"] == 1]
    counts = out["issue_tipo"].value_counts().rename_axis("tipo").reset_index(name="mensagens")
    return counts.sort_values("mensagens", ascending=False)


def kpis(df: pd.DataFrame) -> dict:
    total_sessoes = len(df)
    tempo_resposta = df["first_response_seconds"].dropna()
    return {
        "total_sessoes": total_sessoes,
        "tempo_resposta_medio_min": round(tempo_resposta.mean() / 60, 1) if not tempo_resposta.empty else None,
        "tempo_resposta_mediano_min": round(tempo_resposta.median() / 60, 1) if not tempo_resposta.empty else None,
        "pct_reclamacao": round((df["categoria"] == "reclamacao").mean() * 100, 1) if total_sessoes else 0,
        "pct_duvida": round((df["categoria"] == "duvida").mean() * 100, 1) if total_sessoes else 0,
    }


def volume_por_dia(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["dia"] = out["started_at"].dt.date
    return out.groupby("dia").size().reset_index(name="conversas")


def volume_atendimentos_por_periodo(df: pd.DataFrame, granularidade: str = "dia") -> pd.DataFrame:
    """Como volume_por_dia, mas agregavel tambem por semana/mes - mesmo padrao
    de pico_simultaneos_por_periodo/volume_problemas_por_periodo."""
    out = df.dropna(subset=["started_at"]).copy()
    if out.empty:
        return out.assign(periodo=pd.Series(dtype="object"), conversas=pd.Series(dtype=int))
    if granularidade == "semana":
        out["periodo"] = out["started_at"].dt.to_period("W").dt.start_time.dt.date
    elif granularidade == "mes":
        out["periodo"] = out["started_at"].dt.to_period("M").dt.start_time.dt.date
    else:
        out["periodo"] = out["started_at"].dt.date
    return out.groupby("periodo").size().reset_index(name="conversas")


def volume_por_hora(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["hora"] = out["started_at"].dt.hour
    contagem = out.groupby("hora").size().reindex(range(24), fill_value=0)
    return contagem.rename_axis("hora").reset_index(name="conversas")


# Dom=0 .. Sab=6 (pandas usa Seg=0..Dom=6 - ver _dia_semana_pt).
_DIAS_SEMANA_PT = ["Domingo", "Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado"]

_FAIXA_FORA_HORARIO = "Fora do horário"

# 06h-20h agrupado de 2 em 2 horas; fora disso (20h-06h) tudo em 1 faixa so.
_FAIXAS_HORA_COMERCIAIS = [(6, 8), (8, 10), (10, 12), (12, 14), (14, 16), (16, 18), (18, 20)]
_FAIXAS_HORA_ORDEM = [_FAIXA_FORA_HORARIO] + [f"{ini:02d}h–{fim:02d}h" for ini, fim in _FAIXAS_HORA_COMERCIAIS]


def _dia_semana_pt(timestamp) -> str:
    return _DIAS_SEMANA_PT[(timestamp.dayofweek + 1) % 7]


def _faixa_hora(hora: int) -> str:
    for inicio, fim in _FAIXAS_HORA_COMERCIAIS:
        if inicio <= hora < fim:
            return f"{inicio:02d}h–{fim:02d}h"
    return _FAIXA_FORA_HORARIO


def volume_por_dia_semana_hora(df: pd.DataFrame) -> pd.DataFrame:
    """Heatmap de volume de atendimentos por dia da semana x faixa de horario -
    06h-20h agrupado de 2 em 2 horas, fora disso (20h-06h) tudo em 1 faixa so.
    Sempre devolve as 7x8 combinacoes (fill 0 onde nao houve atendimento)."""
    out = df.dropna(subset=["started_at"]).copy()
    if out.empty:
        return pd.DataFrame(columns=["dia_semana", "faixa_hora", "conversas"])

    out["dia_semana"] = out["started_at"].apply(_dia_semana_pt)
    out["faixa_hora"] = out["started_at"].dt.hour.apply(_faixa_hora)

    contagem = out.groupby(["dia_semana", "faixa_hora"]).size()
    indice_completo = pd.MultiIndex.from_product(
        [_DIAS_SEMANA_PT, _FAIXAS_HORA_ORDEM], names=["dia_semana", "faixa_hora"]
    )
    return contagem.reindex(indice_completo, fill_value=0).reset_index(name="conversas")


def timeline_atendimentos_simultaneos(df: pd.DataFrame) -> pd.DataFrame:
    """Serie temporal (um ponto por inicio/fim de atendimento) com quantos
    atendimentos estavam abertos ao mesmo tempo. Nao distingue atendente -
    mede sobrecarga da fila de suporte como um todo."""
    out = df.dropna(subset=["started_at"]).copy()
    fim = out["ended_at"].fillna(out["started_at"])
    eventos = pd.concat(
        [
            pd.DataFrame({"timestamp": out["started_at"], "delta": 1}),
            pd.DataFrame({"timestamp": fim, "delta": -1}),
        ]
    ).sort_values(["timestamp", "delta"], ascending=[True, False])
    eventos["atendimentos_abertos"] = eventos["delta"].cumsum()
    return eventos[["timestamp", "atendimentos_abertos"]].reset_index(drop=True)


def pico_simultaneos_por_periodo(df: pd.DataFrame, granularidade: str = "dia") -> pd.DataFrame:
    """Pico de atendimentos simultaneos por dia/semana/mes - o maior numero de
    atendimentos abertos ao mesmo tempo observado dentro de cada periodo."""
    timeline = timeline_atendimentos_simultaneos(df)
    if timeline.empty:
        return timeline.rename(columns={"atendimentos_abertos": "pico_simultaneos"}).assign(periodo=None)
    if granularidade == "semana":
        timeline["periodo"] = timeline["timestamp"].dt.to_period("W").dt.start_time.dt.date
    elif granularidade == "mes":
        timeline["periodo"] = timeline["timestamp"].dt.to_period("M").dt.start_time.dt.date
    else:
        timeline["periodo"] = timeline["timestamp"].dt.date
    return (
        timeline.groupby("periodo")["atendimentos_abertos"]
        .max()
        .reset_index(name="pico_simultaneos")
    )


def media_atendimentos_por_hora(df: pd.DataFrame) -> float:
    """Media de atendimentos iniciados por hora do dia - total de atendimentos
    dividido por 24 (mesma base da distribuicao usada em volume_por_hora)."""
    if df.empty:
        return 0.0
    return round(len(df) / 24, 1)


_PALAVRAS_PROBLEMA = [
    "senha", "erro", "cpf", "cadastr", "cai", "trava", "nao consig", "não consig",
    "nao aparece", "não aparece", "nao abre", "não abre", "nao funciona", "não funciona",
    "invalid", "exclu", "vincul", "sumi", "bloque", "nao entra", "não entra", "nao carrega",
    "não carrega", "nao salva", "não salva", "bug",
]

# So conta como "pergunta de esclarecimento" quando o suporte sinaliza confusao de
# forma explicita - NAO conta perguntas de rotina (pedir cpf, cidade etc.), que sao
# normais mesmo numa demanda clara e nao devem inflar o indicador.
_PERGUNTA_ESCLARECIMENTO_RE = re.compile(
    r"nao entendi|não entendi|pode\s+(explicar|detalhar)\s+melhor|nao ficou claro|"
    r"não ficou claro|explica\s+melhor|em que parte exatamente|que parte exatamente|"
    r"nao entendi bem|não entendi bem|nao sei do que|não sei do que|"
    r"o que (voce|você) quer dizer",
    re.IGNORECASE,
)
_MIN_PALAVRAS_MENSAGEM_CLARA = 5


def _mensagem_inicial_vaga(texto) -> bool:
    if not isinstance(texto, str) or not texto.strip():
        return True
    lowered = texto.lower()
    if any(p in lowered for p in _PALAVRAS_PROBLEMA):
        return False
    palavras = [t for t in re.findall(r"\w+", lowered) if not t.isdigit()]
    return len(palavras) < _MIN_PALAVRAS_MENSAGEM_CLARA


def demandas_pouco_claras(conn) -> pd.DataFrame:
    """Heuristica local (sem LLM) pra sinalizar atendimentos cuja demanda inicial
    parece pouco detalhada/confusa - usa dois sinais objetivos:
    - todas as mensagens do cliente antes da 1a resposta do suporte, juntas, ainda
      curtas/sem palavra-chave de problema (nao olha so a 1a mensagem isolada, porque
      "Bom dia" antes de explicar o problema e um padrao normal de conversa, nao sinal
      de demanda confusa)
    - suporte precisou dizer explicitamente que nao entendeu / pedir pra detalhar melhor
    Um atendimento marcado assim nao significa necessariamente demanda ruim, so que
    faltou detalhe de cara - vale conferir manualmente os casos limitrofes.
    Ver docs/demanda-pouco-clara.md para a explicacao completa da regra."""
    rows = conn.execute(
        "SELECT session_id, timestamp, is_support, content FROM messages "
        "WHERE is_media = 0 ORDER BY session_id, timestamp"
    ).fetchall()

    sessions = {}
    for row in rows:
        s = sessions.setdefault(
            row["session_id"],
            {"session_id": row["session_id"], "mensagens_iniciais": [], "suporte_respondeu": False,
             "perguntas_esclarecimento": 0},
        )
        if not row["is_support"] and not s["suporte_respondeu"]:
            s["mensagens_iniciais"].append(row["content"])
        elif row["is_support"]:
            s["suporte_respondeu"] = True
            if _PERGUNTA_ESCLARECIMENTO_RE.search(row["content"] or ""):
                s["perguntas_esclarecimento"] += 1

    out = pd.DataFrame(sessions.values())
    if out.empty:
        return out
    out["mensagem_inicial"] = out["mensagens_iniciais"].apply(
        lambda msgs: "\n".join(msgs) if msgs else None
    )
    out["mensagem_vaga"] = out["mensagem_inicial"].apply(_mensagem_inicial_vaga)
    out["demanda_pouco_clara"] = out["mensagem_vaga"] | (out["perguntas_esclarecimento"] >= 1)
    return out.drop(columns="mensagens_iniciais")


def ranking_temas(df: pd.DataFrame, top_n=8) -> pd.DataFrame:
    counts = df["tema"].value_counts().rename_axis("tema").reset_index(name="conversas")
    if len(counts) > top_n:
        head = counts.iloc[:top_n]
        outros_total = counts.iloc[top_n:]["conversas"].sum()
        outros = pd.DataFrame([{"tema": "Outros", "conversas": outros_total}])
        counts = pd.concat([head, outros], ignore_index=True)
    return counts


def distribuicao_sentimento(df: pd.DataFrame) -> pd.DataFrame:
    counts = df["sentimento"].value_counts().reindex(["positivo", "neutro", "negativo"], fill_value=0)
    return counts.rename_axis("sentimento").reset_index(name="conversas")


def load_group_messages(conn) -> pd.DataFrame:
    return pd.read_sql_query(
        "SELECT * FROM group_messages WHERE is_media = 0", conn, parse_dates=["timestamp", "analyzed_at"]
    )


def deduplicar_incidentes(df: pd.DataFrame) -> pd.DataFrame:
    """Colapsa mensagens de erro/reclamacao da mesma conversa, mesmo tipo e mesmo dia em um
    unico incidente, para nao contar cada resposta/confirmacao da thread como um problema novo."""
    out = df[df["is_issue"] == 1].copy()
    if out.empty:
        return out.assign(mensagens=pd.Series(dtype=int))
    out["dia"] = out["timestamp"].dt.date
    chave_tipo = out["issue_tipo"].fillna(out["issue_categoria"]).fillna("indefinido")
    return (
        out.assign(_tipo_chave=chave_tipo)
        .sort_values("timestamp")
        .groupby(["conversation_id", "_tipo_chave", "dia"], as_index=False)
        .agg(
            id=("id", "first"),
            timestamp=("timestamp", "first"),
            area=("area", "first"),
            issue_categoria=("issue_categoria", "first"),
            issue_tipo=("issue_tipo", "first"),
            issue_tema=("issue_tema", "first"),
            mensagens=("id", "count"),
        )
        .drop(columns="_tipo_chave")
    )


def mesclar_incidentes_semelhantes(incidentes: pd.DataFrame, conn, threshold: float = 0.35) -> pd.DataFrame:
    """Mescla incidentes da mesma conversa e mesmo dia cujo texto representativo e
    semanticamente parecido (similaridade de cosseno TF-IDF >= threshold), mesmo que
    tenham sido classificados com issue_tipo/tema diferentes. Requer que
    pipeline/embeddings.py ja tenha indexado as mensagens; sem indice, retorna
    os incidentes sem alteracao."""
    from pipeline.embeddings import load_all_vectors

    if incidentes.empty:
        return incidentes

    ids, matrix = load_all_vectors(conn)
    if not ids:
        return incidentes
    id_to_row = {mid: i for i, mid in enumerate(ids)}

    incidentes = incidentes.reset_index(drop=True)
    parent = list(range(len(incidentes)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for (conv, dia), group in incidentes.groupby(["conversation_id", "dia"]):
        rows = group.index.tolist()
        vecs = []
        for r in rows:
            mid = incidentes.at[r, "id"]
            row_idx = id_to_row.get(mid)
            vecs.append(matrix[row_idx] if row_idx is not None else None)
        for i in range(len(rows)):
            if vecs[i] is None:
                continue
            for j in range(i + 1, len(rows)):
                if vecs[j] is None:
                    continue
                if float(vecs[i] @ vecs[j]) >= threshold:
                    union(rows[i], rows[j])

    groups = {}
    for idx in incidentes.index:
        root = find(idx)
        groups.setdefault(root, []).append(idx)

    merged_rows = []
    for members in groups.values():
        sub = incidentes.loc[members]
        first = sub.iloc[0].to_dict()
        first["mensagens"] = int(sub["mensagens"].sum())
        merged_rows.append(first)

    return pd.DataFrame(merged_rows)


def kpis_grupos(df: pd.DataFrame) -> dict:
    total = len(df)
    incidentes = deduplicar_incidentes(df)
    total_problemas = len(incidentes)
    return {
        "total_mensagens": total,
        "total_problemas": total_problemas,
        "pct_problemas": round(total_problemas / total * 100, 1) if total else 0,
        "pct_erro_app": round((incidentes["issue_categoria"] == "erro_app").mean() * 100, 1)
        if total_problemas
        else 0,
        "pct_processo_publico": round((incidentes["issue_categoria"] == "processo_publico").mean() * 100, 1)
        if total_problemas
        else 0,
    }


def volume_problemas_por_area(df: pd.DataFrame) -> pd.DataFrame:
    incidentes = deduplicar_incidentes(df)
    return (
        incidentes.groupby("area").size().reset_index(name="problemas").sort_values("problemas", ascending=False)
    )


def distribuicao_categoria_grupos(df: pd.DataFrame) -> pd.DataFrame:
    incidentes = deduplicar_incidentes(df)
    counts = incidentes["issue_categoria"].value_counts().rename_axis("categoria").reset_index(name="incidentes")
    return counts


def distribuicao_tipo_erro_grupos(df: pd.DataFrame) -> pd.DataFrame:
    incidentes = deduplicar_incidentes(df)
    counts = incidentes["issue_tipo"].value_counts().rename_axis("tipo").reset_index(name="incidentes")
    return counts.sort_values("incidentes", ascending=False)


def volume_problemas_por_periodo(df: pd.DataFrame, granularidade: str = "dia") -> pd.DataFrame:
    incidentes = deduplicar_incidentes(df)
    if incidentes.empty:
        return incidentes.assign(periodo=pd.Series(dtype="object")).rename(columns={"mensagens": "problemas"})
    if granularidade == "semana":
        incidentes["periodo"] = incidentes["timestamp"].dt.to_period("W").dt.start_time.dt.date
    elif granularidade == "mes":
        incidentes["periodo"] = incidentes["timestamp"].dt.to_period("M").dt.start_time.dt.date
    else:
        incidentes["periodo"] = incidentes["timestamp"].dt.date
    return incidentes.groupby("periodo").size().reset_index(name="problemas")
