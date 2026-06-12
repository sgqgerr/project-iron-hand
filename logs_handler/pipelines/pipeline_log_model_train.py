from zenml import pipeline
from logs_handler.steps.step_df_log_generator import step_df_log_generator
from logs_handler.steps.step_df_log_preprocessor import step_df_log_preprocessor
from logs_handler.steps.step_model_log_train import step_model_log_train
from logs_handler.steps.step_df_log_parser import step_df_log_parser


@pipeline
def pipeline_log_model_train(
    log_path: str,
    case_id: str,
    y_train,
) -> None:

    features = step_df_log_parser(log_path=log_path, case_id=case_id, to_redis=True)

    step_df_log_generator(features=features, case_id=case_id)

    X, _ = step_df_log_preprocessor(case_id=case_id)

    step_model_log_train(X_train=X, y_train=y_train)