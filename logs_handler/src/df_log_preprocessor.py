import os

from sklearn.preprocessing import StandardScaler, FunctionTransformer
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline

import joblib as jl
import pandas as pd

class DFLogPreprocessor():

    NUMERIC_FEATURES = ["count_failed_logins"]

    BOOL_FEATURES = ["brute_force", "shh_login",
                     "new_systemd_service", "log_tampering",
                     "new_cron_job", "encoded_cmd"]

    FEATURE_ORDER = NUMERIC_FEATURES + BOOL_FEATURES

    def __init__(self , case_id):

        self.case_id = case_id

        self.data_path = f"temp/logs_df_{self.case_id}.csv"

        self.pipeline_path = f"models/preprocessor_pipeline.pkl"

        try :

            self.log_preprocessor = jl.load(f"models/preprocessor_pipeline.pkl")

        except FileNotFoundError:

            self.log_preprocessor = None


    def _load_data(self) -> pd.DataFrame:

        return pd.read_csv(self.data_path)

    def _create_processor(self) -> Pipeline:

        preprocessor = ColumnTransformer(
            transformers=[
                ("num",
                 StandardScaler(),
                 self.NUMERIC_FEATURES),

                ("bool",
                 FunctionTransformer(
                     lambda x: x.astype(int)
                 ),
                 self.BOOL_FEATURES)
            ],

            remainder="drop"
        )

        return Pipeline(
            [("preprocessor", preprocessor)]
        )

    def log_preprocessor(self):

        df = self._load_data(self.data_path)

        if df.empty:

            raise ValueError(f"Dataset for case {self.case_id} not found.")

        case_id = df["CASE_ID"]

        X = df.drop(columns="CASE_ID")

        missing_columns = (
            set(self.FEATURE_ORDER) -
            set(X.columns)
        )

        if missing_columns:

            raise ValueError(f"Missing columns for case {self.case_id}.")

        X = [self.FEATURE_ORDER]

        if self.log_preprocessor is None:

            self.log_preprocessor = (

                self._create_processor()

            )

            self.log_preprocessor.fit(X)

            os.makedirs(os.path.dirname(self.pipeline_path), exist_ok=True)

            jl.dump(self.log_preprocessor, self.pipeline_path)

        X_transformed = self.log_preprocessor.transform(X)

        feature_names = (self.log_preprocessor.get_feature_names_out())

        X_final = pd.DataFrame(X_transformed, columns = feature_names,
                               index = X.index)

        return X_final , case_id

df_log_preprocessor = DFLogPreprocessor()