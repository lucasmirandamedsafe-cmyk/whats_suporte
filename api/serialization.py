"""Conversao de valores pandas/numpy para tipos nativos serializaveis em JSON.

Usado por todos os routers antes de devolver qualquer DataFrame como resposta -
centraliza o unico "gotcha" real de expor pandas via API: NaN/NaT nao sao JSON
valido, e tipos numpy (int64/float64/bool_) nao sao serializaveis por padrao.
"""
from datetime import date, datetime

import numpy as np
import pandas as pd


def _to_native(value):
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, pd.Period):
        return str(value)
    return value


def df_to_records(df: pd.DataFrame) -> list[dict]:
    if df is None or df.empty:
        return []
    records = df.to_dict(orient="records")
    return [{k: _to_native(v) for k, v in row.items()} for row in records]
