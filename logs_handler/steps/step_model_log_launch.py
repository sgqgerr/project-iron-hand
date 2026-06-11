from zenml import step
from logs_handler.src.model_log_train_launch import log_model_train_launch
import pandas as pd


@step
def step_model_log_launch(
    X: pd.DataFrame,
    case_ids: pd.Series,
) -> dict:
    result = log_model_train_launch.predict(X=X)
    result["case_id"] = case_ids.iloc[0] if not case_ids.empty else None
    return result