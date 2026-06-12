from zenml import step
from logs_handler.src.df_log_preprocessor import DFLogPreprocessor
import pandas as pd


@step
def step_df_log_preprocessor(case_id: str) -> tuple[pd.DataFrame, pd.Series]:

    preprocessor = DFLogPreprocessor(case_id=case_id)

    X, case_ids  = preprocessor.log_preprocessor()

    return X, case_ids