from zenml import step
from logs_handler.src.model_log_train_launch import LogModelTrainLaunch
import pandas as pd


@step
def step_model_log_launch(
    X: pd.DataFrame,
    case_ids: pd.Series,
) -> dict:

    launcher = LogModelTrainLaunch(X_train=None, y_train=None)

    if launcher.model is None:

        return {
            "score":   None,
            "case_id": case_ids.iloc[0] if not case_ids.empty else None,
            "error":   "model not found — run training first",
        }

    result = launcher.predict(X)

    result["case_id"] = case_ids.iloc[0] if not case_ids.empty else None

    return result