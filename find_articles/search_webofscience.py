"""Coleta Web of Science via WOS Starter API (Clarivate).

Autenticação
------------
Defina WOS_API_KEY com a chave recebida após aprovação em
https://developer.clarivate.com/  (produto "Web of Science Starter API").

Sintaxe de query
----------------
A WOS Starter API exige field tags do WOS.  Usamos TS= (Topic Search),
que busca título, resumo, keywords de autor e KeyWords Plus.
Exemplo: TS=("quantum machine learning" AND medicine)

Paginação
---------
A API retorna até 50 registros por página.  O campo metadata.total indica
o total de hits; iteramos até cobrir tudo ou até receber lista vazia.
"""
import os
import time

import requests

from common import normalize_text, write_results


# WOS Starter API: query com TS= (Topic Search).
# A API tem limite de tamanho de query — usamos sub-queries curtas e
# acumulamos os resultados deduplicando por wos_id/doi no final.
_QML_GROUPS = [
    '"quantum machine learning" OR QML',
    '"variational quantum" OR VQC OR QNN OR "quantum neural network"',
    '"quantum kernel" OR QSVM OR "quantum support vector machine"',
    '"parameterized quantum circuit" OR PQC OR QAOA OR "quantum classifier"',
]

_MED_GROUPS = [
    'medicine OR medical OR healthcare OR clinical',
    'diagnosis OR prognosis OR radiology OR imaging',
    'MRI OR CT OR ultrasound OR pathology OR histopathology',
    'ECG OR EEG OR genomics OR proteomics OR bioinformatics',
    '"electronic health record" OR EHR OR pharmacology',
]

SUB_QUERIES = [
    f"({q}) AND ({h})" for q in _QML_GROUPS for h in _MED_GROUPS
]

# Mantemos QUERY para compatibilidade com importações externas
QUERY = SUB_QUERIES[0]


def extract_wos_authors(names_block):
    if not names_block:
        return ""
    authors = []
    for item in (names_block.get("authors") or []):
        name = item.get("displayName") or item.get("wosStandard")
        if name:
            authors.append(name)
    for item in (names_block.get("author") or []):
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
        for item in (identifiers.get("identifier") or []):
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

    kw_value = ""
    if isinstance(keywords, list):
        kw_value = ", ".join(keywords)
    elif isinstance(keywords, dict):
        kw_value = keywords.get("authorKeywords", "") or ""

    return {
        "wos_id": hit.get("uid", ""),
        "title": normalize_text(hit.get("title")),
        "authors": extract_wos_authors(names),
        "source_title": normalize_text(extract_source_title(source)),
        "publication_year": hit.get("publishYear", ""),
        "doi": normalize_text(extract_wos_doi(identifiers)),
        "document_type": normalize_text(hit.get("documentType")),
        "keywords": normalize_text(kw_value),
        "link": extract_links(hit.get("links", [])),
    }


def _fetch_sub_query(api_key, query, page_size, sleep_seconds):
    base_url = "https://api.clarivate.com/apis/wos-starter/v1/documents"
    page = 1
    rows = []
    total_records = None

    while True:
        response = requests.get(
            base_url,
            headers={"X-ApiKey": api_key},
            params={"q": query, "limit": page_size, "page": page, "db": "WOS"},
            timeout=60,
        )

        if response.status_code == 400:
            body = response.text.strip()
            raise RuntimeError(
                f"WOS retornou 400 Bad Request.\n"
                f"Verifique a sintaxe da query: {query}\n"
                f"Resposta: {body[:500]}"
            )
        if response.status_code in (401, 403):
            raise RuntimeError(
                f"WOS retornou {response.status_code}. Chave inválida ou API pendente de aprovação.\n"
                f"Acesse https://developer.clarivate.com/ para verificar o status."
            )
        if response.status_code >= 500:
            body = response.text.strip()
            raise RuntimeError(
                f"WOS retornou erro de servidor {response.status_code}.\n"
                f"Resposta: {body[:500]}"
            )

        response.raise_for_status()
        payload = response.json()

        if total_records is None:
            metadata = payload.get("metadata", {})
            try:
                total_records = int(metadata.get("total", 0))
            except (TypeError, ValueError):
                total_records = 0
            if total_records:
                print(f"[webofscience]   estimado: {total_records} registros.")

        hits = payload.get("hits", [])
        if not hits:
            break

        for hit in hits:
            rows.append(parse_hit(hit))

        if total_records and len(rows) >= total_records:
            break
        if len(hits) < page_size:
            break

        page += 1
        time.sleep(sleep_seconds)

    return rows


def search_webofscience(sub_queries=None, page_size=50, sleep_seconds=1.0):
    api_key = os.getenv("WOS_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Defina a variável de ambiente WOS_API_KEY.\n"
            "Registre-se em https://developer.clarivate.com/ e solicite acesso ao "
            "produto 'Web of Science Starter API'."
        )

    if sub_queries is None:
        sub_queries = SUB_QUERIES

    all_rows = []
    for i, query in enumerate(sub_queries, 1):
        print(f"[webofscience] sub-query {i}/{len(sub_queries)}: {query[:80]}…")
        rows = _fetch_sub_query(api_key, query, page_size, sleep_seconds)
        all_rows.extend(rows)
        print(f"[webofscience] sub-query {i} concluída: {len(rows)} registros (total acumulado: {len(all_rows)}).")

    return write_results(all_rows, ["wos_id", "doi"], "webofscience_QML_medicine_results.csv")


if __name__ == "__main__":
    output, count = search_webofscience()
    print(f"[webofscience] CSV gerado em {output} com {count} artigos.")
