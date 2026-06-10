import logging
import pandas as pd
from sklearn.model_selection import train_test_split

logger = logging.getLogger(__name__)

MEMORY_FEATURE_COLS = [
    "wrong_parent",
    "encoded_cmd",
    "memory_injection",
    "external_connection",
    "suspicious_kernel_module",
    "suspicious_bash_cmd",
    "root_process_from_user",
    "night_creation",
]


class DfMemoryPreprocessor:

    def __init__(self, test_size: float = 0.20, random_state: int = 42):

        self.test_size = test_size

        self.random_state = random_state

    def process(
        self,
        df: pd.DataFrame,
    ) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series, pd.Series]:

        self._validate(df)

        case_id = df["case_id"].reset_index(drop=True) \
            if "case_id" in df.columns \
            else pd.Series(range(len(df)), name="case_id")

        y = df["label"].astype(int)

        X = df[MEMORY_FEATURE_COLS].copy()

        X = self._cast(X)

        logger.info(
            f"Preprocessor: {len(X)} rows | "
            f"features: {list(X.columns)} | "
            f"positive rate: {y.mean():.2%}"
        )

        X_train, X_test, y_train, y_test, idx_train, idx_test = train_test_split(
            X, y, case_id.index,
            test_size=self.test_size,
            random_state=self.random_state,
            stratify=y,
        )

        case_id_test = case_id.iloc[idx_test].reset_index(drop=True)

        logger.info(

            f"Split and train: {len(X_train)} | test: {len(X_test)}"

        )

        return (
            X_train.reset_index(drop=True),
            X_test.reset_index(drop=True),
            y_train.reset_index(drop=True),
            y_test.reset_index(drop=True),
            case_id_test,
        )

    def _validate(self, df: pd.DataFrame) -> None:

        missing = [c for c in MEMORY_FEATURE_COLS + ["label"] if c not in df.columns]

        if missing:

            raise ValueError(f"Missing columns in DataFrame: {missing}")

    @staticmethod
    def _cast(X: pd.DataFrame) -> pd.DataFrame:

        for col in MEMORY_FEATURE_COLS:

            if col in X.columns:

                X[col] = X[col].astype(int)

        return X.astype("float32")