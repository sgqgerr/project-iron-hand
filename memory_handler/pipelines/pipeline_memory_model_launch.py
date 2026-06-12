from zenml import pipeline
from memory_handler.steps.step_df_memory_generator import step_df_memory_generator_from_parsed
from memory_handler.steps.step_df_memory_preprocessor import step_df_memory_preprocessor
from memory_handler.steps.step_model_memory_predict import step_model_memory_predict


@pipeline
def pipeline_memory_model_launch(
    parsed_cases: list,
    labels: list,
    case_id: str,
) -> dict:

    df = step_df_memory_generator_from_parsed(

        parsed_cases=parsed_cases,

        labels=labels,

    )

    X, case_ids = step_df_memory_preprocessor(df=df, case_id=case_id)

    result = step_model_memory_predict(X=X, case_ids=case_ids)

    return result