from zenml import step
from memory_handler.src.df_memory_preprocessor import df_memory_preprocessor
import pandas as pd


@step
def step_df_memory_preprocessor(
    df: pd.DataFrame,
    case_id: str,
) -> tuple[pd.DataFrame, pd.Series]:

    return df_memory_preprocessor.preprocess(df=df, case_id=case_id)