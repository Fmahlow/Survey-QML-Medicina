import argparse

from search_arxiv import search_arxiv
from search_ieee import search_ieee
from search_pubmed import search_pubmed
from search_scopus import search_scopus
from search_springer import search_springer
from search_webofscience import search_webofscience


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
        default=["arxiv", "ieee", "springer", "pubmed", "scopus", "webofscience"],
        help="Selecione quais bases consultar.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    run_selected_databases(args.databases)


if __name__ == "__main__":
    main()
