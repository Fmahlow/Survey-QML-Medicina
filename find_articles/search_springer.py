import os
import time

import requests

from common import normalize_text, write_results


SPRINGER_QUERIES = [
    '"quantum machine learning" medicine',
    '"quantum machine learning" medical',
    '"quantum machine learning" healthcare',
    '"variational quantum" medicine',
    '"variational quantum" medical',
    '"quantum neural network" medicine',
    '"quantum neural network" medical',
    '"quantum kernel" medicine',
    '"quantum kernel" medical',
    'QSVM medicine',
    'QSVM medical',
    '"quantum support vector machine" medicine',
    '"quantum classifier" medicine',
    '"parameterized quantum circuit" medicine',
    '"quantum annealing" medicine',
    'QAOA medicine',
    '"drug discovery" "quantum machine learning"',
    'genomics "quantum machine learning"',
    'bioinformatics "quantum machine learning"',
    'radiology "quantum machine learning"',
    'imaging "quantum machine learning"',
    'pathology "quantum machine learning"',
    'ECG "quantum machine learning"',
    'EEG "quantum machine learning"',
]


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
