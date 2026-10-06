import argparse

from common import START_DATE, search_date
from search_arxiv import QUERY as ARXIV_QUERY, search_arxiv
from search_ieee import QUERY as IEEE_QUERY, search_ieee
from search_pubmed import QUERY as PUBMED_QUERY, search_pubmed
from search_scopus import SCOPUS_QUERIES, search_scopus
from search_springer import SUB_QUERIES as SPRINGER_QUERIES, search_springer
from search_webofscience import SUB_QUERIES as WOS_QUERIES, search_webofscience


def run_selected_databases(databases):
    runners = {
        "arxiv": search_arxiv,
        "ieee": search_ieee,
        "springer": search_springer,
        "pubmed": search_pubmed,
        "scopus": search_scopus,
        "webofscience": search_webofscience,
    }

    for database in databases:
        output, count = runners[database]()
        print(f"[{database}] CSV gerado em {output} com {count} artigos.")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Busca artigos sobre QML aplicado a medicina em multiplas bases."
    )
    parser.add_argument(
        "--databases",
        nargs="+",
        choices=["arxiv", "ieee", "springer", "pubmed", "scopus", "webofscience"],
        default=["arxiv", "ieee", "springer", "pubmed"],
        help="Selecione quais bases consultar.",
    )
    parser.add_argument("--show-queries", action="store_true",
                        help="Exibe strings e recorte sem consultar APIs.")
    return parser.parse_args()


def main():
    args = parse_args()
    if args.show_queries:
        queries = {"arxiv": [ARXIV_QUERY], "ieee": [IEEE_QUERY],
                   "springer": SPRINGER_QUERIES, "pubmed": [PUBMED_QUERY],
                   "scopus": SCOPUS_QUERIES, "webofscience": WOS_QUERIES}
        print(f"Recorte: {START_DATE} até {search_date()}; aplicar também no navegador.")
        print("APIs: filtro local por metadados; datas incompletas exigem triagem.")
        for database in args.databases:
            for query in queries[database]:
                print(f"[{database}] {query}")
        return
    run_selected_databases(args.databases)


if __name__ == "__main__":
    main()
