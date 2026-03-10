import argparse

from search_arxiv import search_arxiv
from search_ieee import search_ieee
from search_pubmed import search_pubmed
from search_springer import search_springer


def run_selected_databases(databases):
    runners = {
        "arxiv": search_arxiv,
        "ieee": search_ieee,
        "springer": search_springer,
        "pubmed": search_pubmed,
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
        choices=["arxiv", "ieee", "springer", "pubmed"],
        default=["arxiv", "ieee", "springer", "pubmed"],
        help="Selecione quais bases consultar.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    run_selected_databases(args.databases)


if __name__ == "__main__":
    main()
