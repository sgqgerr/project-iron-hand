from zenml import step
from logs_handler.src.df_log_generator import DFLogGenerator
import os


@step
def step_df_log_generator(features: dict, case_id: str) -> None:

    os.makedirs("temp", exist_ok=True)

    generator = DFLogGenerator(features=features, case_id=case_id)

    generator.generate_df()