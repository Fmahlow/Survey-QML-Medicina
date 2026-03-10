from pathlib import Path

import pandas as pd


BLOCK_QML = (
    '"quantum machine learning" OR QML OR "variational quantum" OR VQC OR '
    'QNN OR "quantum neural network" OR "quantum kernel" OR QSVM OR '
    '"quantum support vector machine" OR "quantum circuit" OR '
    '"parameterized quantum circuit" OR PQC OR "quantum annealing" OR '
    'QAOA OR "quantum classifier"'
)

BLOCK_MED = (
    'medicine OR medical OR healthcare OR clinical OR diagnosis OR prognosis OR '
    'radiology OR imaging OR MRI OR CT OR ultrasound OR pathology OR histopathology OR '
    'ECG OR EEG OR genomics OR proteomics OR bioinformatics OR '
    '"electronic health record" OR EHR OR drug OR pharmacology'
)

OUTPUT_DIR = Path(__file__).resolve().parent


def normalize_text(value):
    if not value:
        return ""
    return " ".join(str(value).split())


def write_results(rows, subset, output_name):
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.drop_duplicates(subset=subset)
    output = OUTPUT_DIR / output_name
    df.to_csv(output, index=False)
    return output, len(df)
