from zenml import step
from logs_handler.src.log_parser import LogsParser


@step
def step_df_log_parser(
    log_path: str,
    case_id: str,
    to_redis: bool = True,
) -> dict:

    parser = LogsParser(log_path=log_path, to_redis=to_redis)

    parser.case_id = case_id

    features = parser.parse_log_file(log_path=log_path, to_redis=to_redis)

    return features