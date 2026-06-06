import pandas as pd

class DFLogGenerator():

    def __init__(self , features, case_id):

        self.features = features

        self.case_id = case_id

    def _clean_data(self , df : pd.DataFrame) -> pd.DataFrame:

        df.drop(columns = ["total_lines",
                           "log_path",
                           "parsed_at"],
                errors = "ignore")

        df.drop_duplicates()

        numeric_col = ["count_failed_logins"]

        boolean_cols = ["brute_force", "shh_login",
                        "new_systemd_service", "log_tampering"]

        for col in numeric_col:

            if col in df.columns:

                df[col] = pd.to_numeric(df[col], errors='coerce')

                df[col] = df[col].fillna(0)

        for col in boolean_cols:

            if col in df.columns:

                df[col] = df[col].fillna(False).astype(bool)

        return df

    def generate_df(self) -> None:

        df = pd.DataFrame([self.features])

        self._clean_data(df)

        if not df.empty:

            df.insert(0, "CASE_ID", self.case_id)

        df.to_csv(f"temp/logs_df_{self.case_id}.csv" , index = False)

df_log_generator = DFLogGenerator()

