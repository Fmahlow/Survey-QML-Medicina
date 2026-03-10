import os
import time

import requests

from common import BLOCK_MED, BLOCK_QML, normalize_text, write_results


QUERY = f"({BLOCK_QML}) AND ({BLOCK_MED})"


def search_ieee(query=QUERY, batch_size=200, sleep_seconds=1.0):
    api_key = os.getenv("IEEE_API_KEY")
    if not api_key:
        raise RuntimeError("Defina a variável de ambiente IEEE_API_KEY.")

    base_url = "https://ieeexploreapi.ieee.org/api/v1/search/articles"
    start_record = 1
    rows = []

    while True:
        response = requests.get(
            base_url,
            params={
                "apikey": api_key,
                "querytext": query,
                "start_record": start_record,
                "max_records": batch_size,
                "format": "json",
            },
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
        articles = payload.get("articles", [])

        if not articles:
            break

        for article in articles:
            authors = article.get("authors", {}).get("authors", [])
            rows.append(
                {
                    "article_number": article.get("article_number", ""),
                    "title": normalize_text(article.get("title")),
                    "authors": ", ".join(
                        author.get("full_name", "") for author in authors if author.get("full_name")
                    ),
                    "publication_year": article.get("publication_year", ""),
                    "publication_title": article.get("publication_title", ""),
                    "doi": article.get("doi", ""),
                    "abstract": normalize_text(article.get("abstract")),
                    "html_url": article.get("html_url", ""),
                    "pdf_url": article.get("pdf_url", ""),
                }
            )

        start_record += len(articles)
        time.sleep(sleep_seconds)

    return write_results(rows, ["article_number", "doi"], "ieee_QML_medicine_results.csv")


if __name__ == "__main__":
    output, count = search_ieee()
    print(f"[ieee] CSV gerado em {output} com {count} artigos.")
