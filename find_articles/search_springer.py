"""Coleta Springer Nature Meta API v2.

Estratégia de sub-queries
--------------------------
A query combinada com todos os termos QML + Medicina excede o limite da API
free-tier (400 Bad Request) e pode consumir o cota diária de 500 requisições
rapidamente.  Por isso dividimos em sub-queries QML x saúde menores e
acumulamos os resultados, deduplicando por DOI/identificador ao final.

Limite diário (~500 req/dia no plano gratuito)
-----------------------------------------------
Cada execução usa no máximo SPRINGER_MAX_REQUESTS requisições no total
(default 80, ~10 req × 8 sub-queries).  Se quiser continuar de onde parou
no dia seguinte, basta executar novamente — os resultados existentes são
mesclados via write_results (deduplicação por identifier/doi).
"""
import os
import time

import requests

from common import BLOCK_MED, BLOCK_QML, normalize_text, write_results


# A Springer Meta API gratuita não suporta field tags (title:/keyword:) —
# a busca é feita em texto livre. Os termos são os mesmos de todas as bases
# (BLOCK_QML e BLOCK_MED de common.py); apenas divididos em sub-queries
# menores para evitar erros de query muito longa.
QML_TERMS = [
    '"quantum machine learning" OR QML',
    '"variational quantum" OR VQC OR QNN OR "quantum neural network"',
    '"quantum kernel" OR QSVM OR "quantum support vector machine" OR "quantum classifier"',
    '"parameterized quantum circuit" OR PQC OR QAOA OR "quantum annealing"',
]

SUB_QUERIES = [f"({q}) AND ({BLOCK_MED})" for q in QML_TERMS]

DEFAULT_BATCH_SIZE = 10           # máximo do plano gratuito Springer
DEFAULT_MAX_REQUESTS_TOTAL = 80   # margem segura dentro dos 500/dia


def raise_for_springer_error(response):
    if response.status_code == 400:
        body = response.text.strip()
        raise RuntimeError(
            f"Springer retornou 400 Bad Request (query inválida?).\n"
            f"Resposta: {body[:500]}"
        )
    if response.status_code in (401, 403, 429):
        body = response.text.strip()
        raise RuntimeError(
            f"Springer retornou {response.status_code}.\n"
            f"Resposta: {body[:500]}"
        )
    response.raise_for_status()


def fetch_sub_query(api_key, query, batch_size, sleep_seconds, max_requests_left):
    """Itera páginas de uma sub-query até esgotar resultados ou cota."""
    base_url = "https://api.springernature.com/meta/v2/json"
    start = 1
    rows = []
    requests_used = 0
    total_records = None

    while True:
        if requests_used >= max_requests_left:
            print(f"[springer] cota de requisições atingida nesta sub-query.")
            break

        response = requests.get(
            base_url,
            params={"q": query, "p": batch_size, "s": start, "api_key": api_key},
            timeout=60,
        )
        requests_used += 1
        raise_for_springer_error(response)
        payload = response.json()

        if total_records is None:
            result_meta = payload.get("result", [{}])
            try:
                total_records = int((result_meta[0] if result_meta else {}).get("total", 0))
            except (TypeError, ValueError):
                total_records = 0
            if total_records:
                print(
                    f"[springer] sub-query estimada: {total_records} registros "
                    f"(batch={batch_size})."
                )

        records = payload.get("records", [])
        if not records:
            break

        for record in records:
            creators = record.get("creators", [])
            rows.append(
                {
                    "search_query": query,
                    "identifier": record.get("identifier", ""),
                    "title": normalize_text(record.get("title")),
                    "authors": ", ".join(c.get("creator", "") for c in creators),
                    "publication_name": record.get("publicationName", ""),
                    "publication_date": record.get("publicationDate", ""),
                    "doi": record.get("doi", ""),
                    "url": ", ".join(u.get("value", "") for u in record.get("url", [])),
                    "abstract": normalize_text(record.get("abstract")),
                    "content_type": record.get("contentType", ""),
                }
            )

        start += len(records)
        if total_records and start > total_records:
            break

        time.sleep(sleep_seconds)

    return rows, requests_used


def search_springer(
    sub_queries=None,
    batch_size=DEFAULT_BATCH_SIZE,
    sleep_seconds=1.0,
    max_requests_total=DEFAULT_MAX_REQUESTS_TOTAL,
):
    api_key = os.getenv("SPRINGER_API_KEY")
    if not api_key:
        raise RuntimeError("Defina a variável de ambiente SPRINGER_API_KEY.")

    max_requests_total = int(os.getenv("SPRINGER_MAX_REQUESTS", max_requests_total))
    batch_size = int(os.getenv("SPRINGER_BATCH_SIZE", batch_size))

    if sub_queries is None:
        sub_queries = SUB_QUERIES

    all_rows = []
    requests_remaining = max_requests_total

    for i, query in enumerate(sub_queries, 1):
        if requests_remaining <= 0:
            print(f"[springer] cota total de {max_requests_total} requisições atingida. "
                  f"Execute novamente amanhã para continuar.")
            break

        print(f"[springer] sub-query {i}/{len(sub_queries)}: {query[:80]}…")
        rows, used = fetch_sub_query(api_key, query, batch_size, sleep_seconds, requests_remaining)
        requests_remaining -= used
        all_rows.extend(rows)
        print(
            f"[springer] sub-query {i} concluída: {len(rows)} registros "
            f"({requests_remaining} requisições restantes hoje)."
        )

    return write_results(all_rows, ["identifier", "doi"], "springer_QML_medicine_results.csv")


if __name__ == "__main__":
    output, count = search_springer()
    print(f"[springer] CSV gerado em {output} com {count} artigos.")
