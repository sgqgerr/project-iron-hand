from zenml import step
from logs_handler.src.df_log_generator import df_log_generator
import pandas as pd


@step
def step_df_log_generator(features: dict, case_id: str) -> pd.DataFrame:

    return df_log_generator.generate_df(features=features, case_id=case_id)