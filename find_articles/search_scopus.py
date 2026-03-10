import os
import time

import requests

from common import BLOCK_MED, BLOCK_QML, normalize_text, write_results


QUERY = f"({BLOCK_QML}) AND ({BLOCK_MED})"


def extract_authors(entry):
    creator = entry.get("dc:creator", "")
    if creator:
        return normalize_text(creator)
    return ""


def extract_link(entry):
    links = entry.get("link", [])
    if isinstance(links, dict):
        links = [links]

    values = []
    for item in links:
        href = item.get("@href")
        if href:
            values.append(href)

    return ", ".join(dict.fromkeys(values))


def parse_entry(entry):
    return {
        "scopus_id": normalize_text(entry.get("dc:identifier", "")),
        "eid": normalize_text(entry.get("eid", "")),
        "title": normalize_text(entry.get("dc:title", "")),
        "authors": extract_authors(entry),
        "publication_name": normalize_text(entry.get("prism:publicationName", "")),
        "cover_date": normalize_text(entry.get("prism:coverDate", "")),
        "doi": normalize_text(entry.get("prism:doi", "")),
        "issn": normalize_text(entry.get("prism:issn", "")),
        "volume": normalize_text(entry.get("prism:volume", "")),
        "issue_identifier": normalize_text(entry.get("prism:issueIdentifier", "")),
        "page_range": normalize_text(entry.get("prism:pageRange", "")),
        "citedby_count": normalize_text(entry.get("citedby-count", "")),
        "subtype_description": normalize_text(entry.get("subtypeDescription", "")),
        "link": extract_link(entry),
    }


def search_scopus(query=QUERY, batch_size=25, sleep_seconds=1.0):
    api_key = os.getenv("SCOPUS_API_KEY")
    if not api_key:
        raise RuntimeError("Defina a variável de ambiente SCOPUS_API_KEY.")

    base_url = "https://api.elsevier.com/content/search/scopus"
    start = 0
    rows = []

    while True:
        response = requests.get(
            base_url,
            headers={
                "X-ELS-APIKey": api_key,
                "Accept": "application/json",
            },
            params={
                "query": query,
                "start": start,
                "count": batch_size,
            },
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json().get("search-results", {})
        entries = payload.get("entry", [])

        if not entries:
            break

        for entry in entries:
            rows.append(parse_entry(entry))

        if len(entries) < batch_size:
            break

        start += len(entries)
        time.sleep(sleep_seconds)

    return write_results(rows, ["scopus_id", "eid", "doi"], "scopus_QML_medicine_results.csv")


if __name__ == "__main__":
    output, count = search_scopus()
    print(f"[scopus] CSV gerado em {output} com {count} artigos.")
