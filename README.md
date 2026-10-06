# Survey-QML-Medicina

As buscas existentes ficam em `find_articles/search_*.py`; os blocos de
termos estão em `find_articles/common.py`.

O escopo é QML aplicado à medicina, abrangendo tarefas, dados e famílias de
métodos. Incluem-se experimentos em simulação ideal/com ruído ou hardware
real e resultados teóricos demonstrados ligados a aplicação médica clara.
Métodos exclusivamente quantum-inspired e propostas sem avaliação ou
resultado teórico demonstrado ficam fora do conjunto principal; propostas
vagas e revisões podem servir como contexto. Não se usa `NOT quantum-inspired`
na recuperação. Annealing/QAOA devem ter componente de aprendizagem;
simulação molecular quântica sem ML e criptografia pós-quântica estão fora.

Período: 01/01/2015 até a data efetiva da busca em 2026. Somente textos
completos em inglês. Preprints arXiv são aceitos, com status de revisão por
pares verificado separadamente. Etapas avaliadas de descoberta de fármacos
são elegíveis; registrar a tarefa concreta sem alegar descoberta real de
medicamento. Dados, splits, encoding, qubits e profundidade são campos de
extração quando aplicáveis, não exigências universais de elegibilidade.

Para inspecionar as strings sem acessar a rede (requer `requirements.txt`):

```sh
python3 find_articles/search_databases.py --show-queries --databases arxiv ieee springer pubmed scopus webofscience
```

Scopus e Web of Science devem ser consultadas pelo navegador institucional,
usando as strings exibidas na busca avançada e aplicando o período na interface.
As APIs continuam disponíveis mediante seleção explícita. O comando de coleta
sem argumentos consulta apenas arXiv, IEEE, Springer e PubMed.

Os coletores aplicam o período localmente antes de salvar, pelos metadados;
`search_date`, `search_start_date`, `search_end_date` e `date_screening` registram
o recorte. Datas ausentes ou incompletas no ano de corte permanecem para
conferência. Idioma do texto completo, método, avaliação e revisão por pares
exigem triagem. Os CSVs antigos não foram regenerados nem filtrados.

Na execução efetiva, salvar as strings exatas, data, filtros da interface,
contagem bruta, contagem exportada, interrupções/limites e motivos de exclusão.
As strings adaptadas ainda precisam de piloto para verificar sintaxe e cobertura
em cada base; preservar papers semente para medir perdas. A Meta API Springer
não garante a cobertura de SpringerLink. Seu limite de requisições pode deixar
a coleta incompleta; repetir reinicia a paginação e substitui o CSV.

`merge_find_articles_csv.py` lê CSVs e salva também
`merged_QML_medicine_all_records.csv` antes da deduplicação, preservando
fontes e versões. Normaliza DOI e sufixos de versão arXiv. O consolidado é
uma lista candidata: correspondências por título e relações preprint/publicação
precisam de conferência; priorizar a versão final revisada por pares quando
confirmada. Exportações `.xls` existentes não são importadas pelo script;
exportar CSV e adequar colunas ao esquema dos coletores antes de consolidar.
