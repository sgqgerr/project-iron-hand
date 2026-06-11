from zenml import step
from logs_handler.src.df_log_preprocessor import df_log_preprocessor
import pandas as pd


@step
def step_df_log_preprocessor(
    df: pd.DataFrame,
    case_id: str,
) -> tuple[pd.DataFrame, pd.Series]:
    return df_log_preprocessor.preprocess(df=df, case_id=case_id)