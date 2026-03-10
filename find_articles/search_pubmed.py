import time

import requests

from common import BLOCK_MED, BLOCK_QML, normalize_text, write_results


QUERY = f"({BLOCK_QML}) AND ({BLOCK_MED})"


def extract_pubmed_doi(article_ids):
    for article_id in article_ids:
        if article_id.get("idtype") == "doi":
            return article_id.get("value", "")
    return ""


def search_pubmed(query=QUERY, batch_size=200, sleep_seconds=0.34):
    search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    summary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"

    search_response = requests.get(
        search_url,
        params={
            "db": "pubmed",
            "term": query,
            "retmode": "json",
            "retmax": 0,
        },
        timeout=60,
    )
    search_response.raise_for_status()
    total_count = int(search_response.json()["esearchresult"]["count"])

    rows = []
    retstart = 0

    while retstart < total_count:
        batch_response = requests.get(
            search_url,
            params={
                "db": "pubmed",
                "term": query,
                "retmode": "json",
                "retstart": retstart,
                "retmax": batch_size,
            },
            timeout=60,
        )
        batch_response.raise_for_status()
        id_list = batch_response.json()["esearchresult"].get("idlist", [])

        if not id_list:
            break

        summary_response = requests.get(
            summary_url,
            params={
                "db": "pubmed",
                "id": ",".join(id_list),
                "retmode": "json",
            },
            timeout=60,
        )
        summary_response.raise_for_status()
        summary_payload = summary_response.json().get("result", {})

        for pmid in id_list:
            article = summary_payload.get(pmid, {})
            authors = article.get("authors", [])
            rows.append(
                {
                    "pmid": pmid,
                    "title": normalize_text(article.get("title")),
                    "authors": ", ".join(author.get("name", "") for author in authors),
                    "pubdate": article.get("pubdate", ""),
                    "fulljournalname": article.get("fulljournalname", ""),
                    "doi": extract_pubmed_doi(article.get("articleids", [])),
                    "article_type": ", ".join(article.get("pubtype", [])),
                    "link": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                }
            )

        retstart += len(id_list)
        time.sleep(sleep_seconds)

    return write_results(rows, ["pmid"], "pubmed_QML_medicine_results.csv")


if __name__ == "__main__":
    output, count = search_pubmed()
    print(f"[pubmed] CSV gerado em {output} com {count} artigos.")
