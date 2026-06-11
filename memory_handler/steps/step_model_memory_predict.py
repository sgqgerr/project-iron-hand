from zenml import step
from memory_handler.src.model_memory_train_launch import model_train_launch
import pandas as pd


@step
def step_model_memory_predict(
    X: pd.DataFrame,
    case_ids: pd.Series,
) -> dict:

    result = model_train_launch.predict(X=X)

    result["case_id"] = case_ids.iloc[0] if not case_ids.empty else None

    return result