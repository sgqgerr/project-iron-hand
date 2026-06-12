from zenml import step
from logs_handler.src.model_log_train_launch import LogModelTrainLaunch
import pandas as pd


@step
def step_model_log_train(
    X_train: pd.DataFrame,
    y_train: pd.Series,
) -> None:

    LogModelTrainLaunch(X_train=X_train, y_train=y_train)