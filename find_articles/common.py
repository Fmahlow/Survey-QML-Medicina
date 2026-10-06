from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
import re

import pandas as pd


# Preserve the existing terms, sharing the same coverage across split queries.
QML_GROUPS = [
    '"quantum machine learning" OR QML',
    '"variational quantum" OR VQC OR QNN OR "quantum neural network"',
    '"quantum kernel" OR QSVM OR "quantum support vector machine"',
    '"quantum circuit" OR "parameterized quantum circuit" OR PQC',
    '"quantum annealing" OR QAOA OR "quantum classifier"',
]
MED_GROUPS = [
    'medicine OR medical OR healthcare OR health OR biomedical OR clinical',
    'diagnosis OR prognosis OR disease OR radiology OR imaging',
    'MRI OR CT OR ultrasound OR pathology OR histopathology',
    'ECG OR EEG OR genomics OR proteomics OR bioinformatics',
    '"electronic health record" OR EHR',
    'drug OR pharmacology OR pharmaceutical OR therapeutic OR "drug discovery" OR '
    '"drug design" OR "drug screening" OR "molecular property" OR "protein folding"',
]
BLOCK_QML = " OR ".join(QML_GROUPS)
BLOCK_MED = " OR ".join(MED_GROUPS)
START_DATE = "2015-01-01"


def search_date():
    """Use the user's timezone; evaluate when collecting, not at module import."""
    return datetime.now(ZoneInfo("America/Sao_Paulo")).date().isoformat()


def date_status(row, cutoff):
    """Filter known dates only; incomplete dates need full-text screening."""
    for field in ("published", "publication_date", "cover_date", "pubdate", "publication_year"):
        value = str(row.get(field, "") or "").strip()
        if not value:
            continue
        match = re.search(r"\b(19|20)\d{2}\b", value)
        if not match:
            continue
        year = int(match.group())
        if year < 2015 or year > int(cutoff[:4]):
            return "outside_range"
        if re.fullmatch(r"\d{4}", value):
            return "year_only_verify_cutoff" if year == int(cutoff[:4]) else "year_in_range"
        # ISO timestamps and PubMed textual dates; do not guess date ranges.
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}(?:T.*)?", value):
            date = value[:10]
        elif re.fullmatch(r"\d{4} [A-Za-z]{3} \d{1,2}", value):
            parsed = pd.to_datetime(value, format="%Y %b %d", errors="coerce")
            date = parsed.date().isoformat() if not pd.isna(parsed) else None
        else:
            date = None
        if date:
            return "in_range" if START_DATE <= date <= cutoff else "outside_range"
        return "year_only_verify_cutoff" if year == int(cutoff[:4]) else "year_in_range"
    return "missing_date_verify"


OUTPUT_DIR = Path(__file__).resolve().parent


def normalize_text(value):
    if not value:
        return ""
    return " ".join(str(value).split())


def write_results(rows, subset, output_name):
    cutoff = search_date()
    df = pd.DataFrame(rows)
    if not df.empty:
        df["date_screening"] = [date_status(row, cutoff) for row in rows]
        df = df[df["date_screening"] != "outside_range"].copy()
    df["search_date"] = cutoff
    df["search_start_date"] = START_DATE
    df["search_end_date"] = cutoff
    if not df.empty:
        df = df.drop_duplicates(subset=subset)
    output = OUTPUT_DIR / output_name
    df.to_csv(output, index=False)
    return output, len(df)
