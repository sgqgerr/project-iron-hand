from zenml import pipeline
from logs_handler.steps.step_df_log_generator import step_df_log_generator
from logs_handler.steps.step_df_log_preprocessor import step_df_log_preprocessor
from logs_handler.steps.step_model_log_launch import step_model_log_launch
from logs_handler.steps.step_df_log_parser import step_df_log_parser


@pipeline
def pipeline_log_model_predict(
    log_path: str,
    case_id: str,
) -> dict:

    features = step_df_log_parser(log_path=log_path, case_id=case_id, to_redis=True)

    step_df_log_generator(features=features, case_id=case_id)

    X, case_ids = step_df_log_preprocessor(case_id=case_id)

    result = step_model_log_launch(X=X, case_ids=case_ids)

    return result