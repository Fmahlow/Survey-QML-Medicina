import os
import time

import requests

from common import BLOCK_MED, BLOCK_QML, normalize_text, write_results


QUERY = f"({BLOCK_QML}) AND ({BLOCK_MED})"


def search_springer(query=QUERY, batch_size=100, sleep_seconds=1.0):
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
                "api_key": api_key,
                "q": query,
                "p": batch_size,
                "s": start,
            },
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
        records = payload.get("records", [])

        if not records:
            break

        for record in records:
            creators = record.get("creators", [])
            rows.append(
                {
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
