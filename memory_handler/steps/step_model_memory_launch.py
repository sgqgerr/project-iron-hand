from zenml import step
from memory_handler.src.model_memory_train_launch import model_train_launch
import pandas as pd


@step
def step_model_memory_train(
    X_train: pd.DataFrame,
    y_train: pd.Series,
) -> None:
    model_train_launch.train(X_train=X_train, y_train=y_train)