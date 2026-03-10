import os
import time

import requests

from common import normalize_text, write_results


SPRINGER_QUERIES = [
    '"quantum machine learning"',
    '"variational quantum"',
    '"quantum neural network"',
    '"quantum kernel"',
    'QSVM',
    '"quantum support vector machine"',
    '"quantum classifier"',
    '"parameterized quantum circuit"',
    '"quantum annealing"',
    'QAOA',
]

MEDICAL_TERMS = [
    "medicine",
    "medical",
    "healthcare",
    "clinical",
    "diagnosis",
    "prognosis",
    "radiology",
    "imaging",
    "mri",
    "ct",
    "ultrasound",
    "pathology",
    "histopathology",
    "ecg",
    "eeg",
    "genomics",
    "proteomics",
    "bioinformatics",
    "electronic health record",
    "ehr",
    "drug",
    "pharmacology",
]


def is_medical_record(record):
    fields = [
        record.get("title", ""),
        record.get("abstract", ""),
        " ".join(record.get("keyword", [])),
        " ".join(record.get("subjects", [])),
    ]
    haystack = " ".join(normalize_text(field).lower() for field in fields)
    return any(term in haystack for term in MEDICAL_TERMS)


def raise_for_springer_error(response):
    if response.status_code == 401:
        body = response.text.strip()
        detail = body[:300] if body else "sem corpo de resposta"
        raise RuntimeError(
            "Springer retornou 401 Unauthorized. A chave foi enviada, mas nao esta "
            "autorizada para este endpoint. Verifique se a chave esta ativa no "
            "portal do Springer Nature e se corresponde a Meta API. "
            f"Resposta: {detail}"
        )
    if response.status_code == 403:
        body = response.text.strip()
        detail = body[:300] if body else "sem corpo de resposta"
        raise RuntimeError(
            "Springer retornou 403 Forbidden ao acessar a Meta API. "
            "A chave foi aceita, mas esta consulta especifica foi bloqueada. "
            "Tente reduzir a query ou verificar limites do plano. "
            f"Resposta: {detail}"
        )
    response.raise_for_status()


def search_springer(queries=None, batch_size=100, sleep_seconds=1.0):
    api_key = os.getenv("SPRINGER_API_KEY")
    if not api_key:
        raise RuntimeError("Defina a variável de ambiente SPRINGER_API_KEY.")

    if queries is None:
        queries = SPRINGER_QUERIES

    base_url = "https://api.springernature.com/meta/v2/json"
    rows = []

    for query in queries:
        start = 1

        while True:
            response = requests.get(
                base_url,
                params={
                    "api_key": api_key,
                    "q": query,
                    "p": batch_size,
                    "s": start,
                },
                timeout=60,
            )
            try:
                raise_for_springer_error(response)
            except RuntimeError as exc:
                print(f"[springer] pulando query {query!r}: {exc}")
                break

            payload = response.json()
            records = payload.get("records", [])

            if not records:
                break

            for record in records:
                if not is_medical_record(record):
                    continue

                creators = record.get("creators", [])
                rows.append(
                    {
                        "search_query": query,
                        "identifier": record.get("identifier", ""),
                        "title": normalize_text(record.get("title")),
                        "authors": ", ".join(creator.get("creator", "") for creator in creators),
                        "publication_name": record.get("publicationName", ""),
                        "publication_date": record.get("publicationDate", ""),
                        "doi": record.get("doi", ""),
                        "url": ", ".join(url.get("value", "") for url in record.get("url", [])),
                        "abstract": normalize_text(record.get("abstract")),
                        "content_type": record.get("contentType", ""),
                    }
                )

            start += len(records)
            time.sleep(sleep_seconds)

    return write_results(rows, ["identifier", "doi"], "springer_QML_medicine_results.csv")


if __name__ == "__main__":
    output, count = search_springer()
    print(f"[springer] CSV gerado em {output} com {count} artigos.")
