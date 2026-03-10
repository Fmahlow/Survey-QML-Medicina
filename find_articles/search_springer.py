import os
import time

import requests

from common import normalize_text, write_results


QML_BLOCK = (
    '"quantum machine learning" OR QML OR "variational quantum" OR VQC OR '
    'QNN OR "quantum neural network" OR "quantum kernel" OR QSVM OR '
    '"quantum support vector" OR "quantum circuit" OR '
    '"parameterized quantum circuit" OR PQC OR "quantum annealing" OR '
    'QAOA OR "quantum classifier"'
)

HEALTH_BLOCK = (
    'medicine OR medical OR healthcare OR clinical OR diagnosis OR prognosis OR '
    'radiology OR imaging OR MRI OR CT OR ultrasound OR pathology OR '
    'histopathology OR ECG OR EEG OR genomics OR proteomics OR bioinformatics OR '
    '"electronic health record" OR EHR OR drug OR pharmacology'
)

QUERY = f"({QML_BLOCK}) AND ({HEALTH_BLOCK})"


def raise_for_springer_error(response):
    if response.status_code in (401, 403):
        body = response.text.strip()
        detail = body[:500] if body else "sem corpo de resposta"
        raise RuntimeError(f"Springer retornou {response.status_code}. Resposta: {detail}")
    response.raise_for_status()


def search_springer(query=QUERY, batch_size=10, sleep_seconds=1.0):
    api_key = os.getenv("SPRINGER_API_KEY")
    if not api_key:
        raise RuntimeError("Defina a variável de ambiente SPRINGER_API_KEY.")

    base_url = "https://api.springernature.com/meta/v2/json"
    start = 1
    rows = []

    while True:
        response = requests.get(
            base_url,
            params={
                "q": query,
                "p": batch_size,
                "s": start,
                "api_key": api_key,
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
