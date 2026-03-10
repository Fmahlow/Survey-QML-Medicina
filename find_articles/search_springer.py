import os
import time

import requests

from common import normalize_text, write_results


SPRINGER_QUERIES = [
    '"quantum machine learning" AND medicine',
    '"quantum machine learning" AND medical',
    '"quantum machine learning" AND healthcare',
    '"variational quantum" AND medicine',
    '"variational quantum" AND medical',
    '"quantum neural network" AND medicine',
    '"quantum neural network" AND medical',
    '"quantum kernel" AND medicine',
    '"quantum kernel" AND medical',
    'QSVM AND medicine',
    'QSVM AND medical',
    '"quantum support vector machine" AND medicine',
    '"quantum classifier" AND medicine',
    '"parameterized quantum circuit" AND medicine',
    '"quantum annealing" AND medicine',
    'QAOA AND medicine',
    '"drug discovery" AND "quantum machine learning"',
    'genomics AND "quantum machine learning"',
    'bioinformatics AND "quantum machine learning"',
    'radiology AND "quantum machine learning"',
    'imaging AND "quantum machine learning"',
    'pathology AND "quantum machine learning"',
    'ECG AND "quantum machine learning"',
    'EEG AND "quantum machine learning"',
]


def raise_for_springer_error(response):
    if response.status_code == 401:
        body = response.text.strip()
        detail = body[:300] if body else "sem corpo de resposta"
        raise RuntimeError(
            "Springer retornou 401 Unauthorized. A chave foi enviada, mas nao esta "
            "autorizada para este endpoint/plano. Verifique se a chave esta ativa no "
            "portal do Springer Nature e se o seu acesso cobre a Meta API. "
            f"Resposta: {detail}"
        )
    if response.status_code == 403:
        body = response.text.strip()
        detail = body[:300] if body else "sem corpo de resposta"
        raise RuntimeError(
            "Springer retornou 403 Forbidden. A chave foi aceita, mas esta consulta "
            "foi bloqueada. Isso costuma acontecer com queries muito longas ou com "
            "sintaxe booleana que a Meta API nao aceita bem. "
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
            raise_for_springer_error(response)
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
