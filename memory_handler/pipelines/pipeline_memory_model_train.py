from zenml import pipeline
from memory_handler.steps.step_df_memory_generator import step_df_memory_generator_synthetic
from memory_handler.steps.step_df_memory_preprocessor import step_df_memory_preprocessor
from memory_handler.steps.step_model_memory_train import step_model_memory_train


@pipeline
def pipeline_memory_model_train(
    case_id: str,
    n: int = 500,
) -> None:

    df = step_df_memory_generator_synthetic(n=n)

    X, _ = step_df_memory_preprocessor(df=df, case_id=case_id)

    step_model_memory_train(X_train=X, y_train=df["label"])