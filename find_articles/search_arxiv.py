import time
import urllib.parse

import feedparser

from common import BLOCK_MED, BLOCK_QML, normalize_text, write_results


QUERY = f'all:({BLOCK_QML}) AND all:({BLOCK_MED})'


def search_arxiv(query=QUERY, batch_size=200, sleep_seconds=1.0):
    encoded_query = urllib.parse.quote(query)
    base_url = "http://export.arxiv.org/api/query?"
    start = 0
    rows = []

    while True:
        url = (
            f"{base_url}search_query={encoded_query}"
            f"&start={start}&max_results={batch_size}"
        )
        feed = feedparser.parse(url)

        if not feed.entries:
            break

        for entry in feed.entries:
            rows.append(
                {
                    "arxiv_id": entry.id.split("/abs/")[-1],
                    "title": normalize_text(entry.title),
                    "authors": ", ".join(a.name for a in entry.authors),
                    "published": entry.published,
                    "categories": ", ".join(tag["term"] for tag in entry.tags),
                    "summary": normalize_text(entry.summary),
                    "link": entry.link,
                }
            )

        start += len(feed.entries)
        time.sleep(sleep_seconds)

    return write_results(rows, ["arxiv_id"], "arxiv_QML_medicine_results.csv")


if __name__ == "__main__":
    output, count = search_arxiv()
    print(f"[arxiv] CSV gerado em {output} com {count} artigos.")
