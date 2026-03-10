import os
import time

import requests

from common import BLOCK_MED, BLOCK_QML, normalize_text, write_results


QUERY = f"({BLOCK_QML}) AND ({BLOCK_MED})"


def extract_wos_authors(names_block):
    if not names_block:
        return ""

    authors = []
    for item in names_block.get("authors", []) or []:
        name = item.get("displayName") or item.get("wosStandard")
        if name:
            authors.append(name)

    for item in names_block.get("author", []) or []:
        name = item.get("displayName") or item.get("fullName") or item.get("wosStandard")
        if name:
            authors.append(name)

    return ", ".join(dict.fromkeys(authors))


def extract_wos_doi(identifiers):
    if not identifiers:
        return ""

    if isinstance(identifiers, dict):
        for key in ("doi", "DOI"):
            value = identifiers.get(key)
            if value:
                return value

        for item in identifiers.get("identifier", []) or []:
            if str(item.get("type", "")).lower() == "doi" and item.get("value"):
                return item["value"]

    if isinstance(identifiers, list):
        for item in identifiers:
            if str(item.get("type", "")).lower() == "doi" and item.get("value"):
                return item["value"]

    return ""


def extract_source_title(source):
    if not source:
        return ""

    if isinstance(source, str):
        return source

    for key in ("sourceTitle", "title", "publishers"):
        value = source.get(key)
        if isinstance(value, str) and value:
            return value

    return ""


def extract_links(links):
    if not links:
        return ""

    if isinstance(links, dict):
        links = [links]

    values = []
    for item in links:
        for key in ("url", "record", "value"):
            value = item.get(key)
            if value:
                values.append(value)

    return ", ".join(dict.fromkeys(values))


def parse_hit(hit):
    identifiers = hit.get("identifiers", {})
    source = hit.get("source", {})
    names = hit.get("names", {})
    keywords = hit.get("keywords", {})

    return {
        "wos_id": hit.get("uid", ""),
        "title": normalize_text(hit.get("title")),
        "authors": extract_wos_authors(names),
        "source_title": normalize_text(extract_source_title(source)),
        "publication_year": hit.get("publishYear", ""),
        "doi": normalize_text(extract_wos_doi(identifiers)),
        "document_type": normalize_text(hit.get("documentType")),
        "keywords": normalize_text(
            ", ".join(keywords) if isinstance(keywords, list) else keywords.get("authorKeywords", "")
            if isinstance(keywords, dict) else ""
        ),
        "link": extract_links(hit.get("links", [])),
    }


def search_webofscience(query=QUERY, page_size=50, sleep_seconds=1.0):
    api_key = os.getenv("WOS_API_KEY")
    if not api_key:
        raise RuntimeError("Defina a variável de ambiente WOS_API_KEY.")

    base_url = "https://api.clarivate.com/apis/wos-starter/v1/documents"
    page = 1
    rows = []

    while True:
        response = requests.get(
            base_url,
            headers={"X-ApiKey": api_key},
            params={
                "q": query,
                "limit": page_size,
                "page": page,
                "db": "WOS",
            },
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
        hits = payload.get("hits", [])

        if not hits:
            break

        for hit in hits:
            rows.append(parse_hit(hit))

        if len(hits) < page_size:
            break

        page += 1
        time.sleep(sleep_seconds)

    return write_results(rows, ["wos_id", "doi"], "webofscience_QML_medicine_results.csv")


if __name__ == "__main__":
    output, count = search_webofscience()
    print(f"[webofscience] CSV gerado em {output} com {count} artigos.")
