from zenml import step
from memory_handler.src.df_memory_generator import df_memory_generator
import pandas as pd


@step
def step_df_memory_generator_synthetic(n: int = 500, seed: int = 42) -> pd.DataFrame:

    return df_memory_generator.synthetic(n=n, seed=seed)


@step
def step_df_memory_generator_from_parsed(
    parsed_cases: list,
    labels: list,
) -> pd.DataFrame:

    return df_memory_generator.from_parsed(parsed_cases=parsed_cases, labels=labels)