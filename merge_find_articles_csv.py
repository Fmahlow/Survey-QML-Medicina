import re
from pathlib import Path

import pandas as pd
from pandas.errors import EmptyDataError


BASE_DIR = Path(__file__).resolve().parent
FIND_ARTICLES_DIR = BASE_DIR / "find_articles"
OUTPUT_FILE = BASE_DIR / "merged_QML_medicine_results.csv"


def normalize_text(value):
    if pd.isna(value):
        return ""
    return " ".join(str(value).strip().split())


def normalize_title(value):
    text = normalize_text(value).lower()
    return re.sub(r"[^a-z0-9]+", "", text)


def normalize_authors(value):
    text = normalize_text(value).lower()
    return re.sub(r"[^a-z0-9,;]+", "", text)


def normalize_doi(value):
    return normalize_text(value).lower()


def infer_source(file_path):
    name = file_path.stem.lower()
    if "arxiv" in name:
        return "arxiv"
    if "pubmed" in name:
        return "pubmed"
    if "ieee" in name:
        return "ieee"
    if "springer" in name:
        return "springer"
    if "scopus" in name:
        return "scopus"
    if "webofscience" in name:
        return "webofscience"
    return name


def infer_year(row):
    for column in ("published", "publication_year", "publication_date", "pubdate"):
        value = normalize_text(row.get(column, ""))
        match = re.search(r"(19|20)\d{2}", value)
        if match:
            return match.group(0)
    return ""


def choose_title(row):
    for column in ("title",):
        value = normalize_text(row.get(column, ""))
        if value:
            return value
    return ""


def choose_link(row):
    for column in ("link", "html_url", "pdf_url", "url"):
        value = normalize_text(row.get(column, ""))
        if value:
            return value
    return ""


def build_unique_key(row):
    title_key = normalize_title(choose_title(row))
    year = infer_year(row)
    doi = normalize_doi(row.get("doi", ""))
    if doi:
        return f"doi:{doi}"

    for column in ("arxiv_id", "pmid", "article_number", "identifier"):
        value = normalize_text(row.get(column, ""))
        if value:
            return f"{column}:{value.lower()}"

    for column in ("wos_id", "scopus_id", "eid"):
        value = normalize_text(row.get(column, ""))
        if value:
            return f"{column}:{value.lower()}"

    if title_key and year:
        return f"title_year:{title_key}:{year}"
    if title_key:
        return f"title:{title_key}"

    return ""


def load_csv(file_path):
    try:
        df = pd.read_csv(file_path)
    except EmptyDataError:
        print(f"[merge] ignorando CSV vazio: {file_path.name}")
        return None

    if df.empty:
        print(f"[merge] ignorando CSV sem registros: {file_path.name}")
        return None

    df["source"] = infer_source(file_path)
    df["origin_file"] = file_path.name
    df["merged_title"] = df.apply(choose_title, axis=1)
    df["merged_year"] = df.apply(infer_year, axis=1)
    df["merged_link"] = df.apply(choose_link, axis=1)
    if "authors" not in df.columns:
        df["authors"] = ""
    if "doi" not in df.columns:
        df["doi"] = ""
    df["normalized_title"] = df["merged_title"].apply(normalize_title)
    df["normalized_authors"] = df["authors"].apply(normalize_authors)
    df["normalized_doi"] = df["doi"].apply(normalize_doi)
    df["unique_key"] = df.apply(build_unique_key, axis=1)
    return df


def dedupe_step(df, columns):
    available = [column for column in columns if column in df.columns]
    if len(available) != len(columns):
        return df

    mask = pd.Series(True, index=df.index)
    for column in available:
        mask &= df[column].fillna("").astype(str).str.strip() != ""

    matched = df[mask]
    unmatched = df[~mask]
    deduped = matched.drop_duplicates(subset=available, keep="first")
    return pd.concat([deduped, unmatched], ignore_index=True, sort=False)


def merge_csvs():
    csv_files = sorted(
        file_path
        for file_path in FIND_ARTICLES_DIR.glob("*.csv")
        if file_path.name != OUTPUT_FILE.name
    )

    if not csv_files:
        raise FileNotFoundError(
            f"Nenhum CSV encontrado em {FIND_ARTICLES_DIR}"
        )

    frames = [load_csv(file_path) for file_path in csv_files]
    frames = [frame for frame in frames if frame is not None]

    if not frames:
        raise RuntimeError("Todos os CSVs encontrados estao vazios ou sem colunas.")

    merged = pd.concat(frames, ignore_index=True, sort=False)

    final_df = merged.copy()
    final_df = dedupe_step(final_df, ["normalized_doi"])
    final_df = dedupe_step(final_df, ["arxiv_id"])
    final_df = dedupe_step(final_df, ["pmid"])
    final_df = dedupe_step(final_df, ["article_number"])
    final_df = dedupe_step(final_df, ["identifier"])
    final_df = dedupe_step(final_df, ["wos_id"])
    final_df = dedupe_step(final_df, ["scopus_id"])
    final_df = dedupe_step(final_df, ["eid"])
    final_df = dedupe_step(final_df, ["normalized_title", "normalized_authors", "merged_year"])
    final_df = dedupe_step(final_df, ["normalized_title", "normalized_authors"])
    final_df = dedupe_step(final_df, ["normalized_title", "merged_year"])
    final_df = dedupe_step(final_df, ["normalized_title"])

    preferred_columns = [
        "source",
        "origin_file",
        "merged_title",
        "merged_year",
        "doi",
        "merged_link",
        "unique_key",
    ]
    other_columns = [column for column in final_df.columns if column not in preferred_columns]
    final_df = final_df[preferred_columns + other_columns]
    final_df.to_csv(OUTPUT_FILE, index=False)

    print(f"Arquivos lidos: {len(csv_files)}")
    print(f"Registros totais antes da deduplicacao: {len(merged)}")
    print(f"Registros apos deduplicacao: {len(final_df)}")
    print(f"CSV consolidado gerado em: {OUTPUT_FILE}")


if __name__ == "__main__":
    merge_csvs()
