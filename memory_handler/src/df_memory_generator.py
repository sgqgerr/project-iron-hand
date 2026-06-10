import pandas as pd
import numpy as np
import random
import logging

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


class DfMemoryGenerator:

    def from_parsed(
        self,
        parsed_cases: list[dict],
        labels: list[int],
    ) -> pd.DataFrame:

        if len(parsed_cases) != len(labels):

            raise ValueError(

                f"parsed_cases length {len(parsed_cases)} "
                
                f"!= labels length {len(labels)}"

            )

        rows = []

        for case, label in zip(parsed_cases, labels):

            row = {"case_id": case["case_id"]}

            row.update(case["features"])

            row["label"] = label

            rows.append(row)

        df = pd.DataFrame(rows)

        df = self._cast_features(df)

        logger.info(f"Generated DataFrame from {len(df)} real cases")

        return df

    def synthetic(self, n: int = 500, seed: int = 42) -> pd.DataFrame:

        random.seed(seed)
        np.random.seed(seed)

        SCENARIOS = {
            "clean":       0.35,
            "rootkit":     0.25,
            "lateral":     0.20,
            "injection":   0.12,
            "persistence": 0.08,
        }

        def wc(d: dict) -> str:

            val = random.random()

            cumulative = 0.0

            for k, v in d.items():

                cumulative += v

                if val < cumulative:

                    return k

            return list(d.keys())[-1]

        def nb(v: bool, p: float = 0.05) -> bool:

            return not v if random.random() < p else v

        rows = []

        for i in range(n):

            s = wc(SCENARIOS)

            cid = f"case-{i + 1:04d}"

            if s == "clean":

                row = dict(
                    wrong_parent=nb(False, 0.03),
                    encoded_cmd=nb(False, 0.03),
                    memory_injection=nb(False, 0.02),
                    external_connection=nb(False, 0.04),
                    suspicious_kernel_module=nb(False, 0.02),
                    suspicious_bash_cmd=nb(False, 0.03),
                    root_process_from_user=nb(False, 0.02),
                    night_creation=nb(False, 0.08),
                    label=0,
                )

            elif s == "rootkit":

                row = dict(
                    wrong_parent=nb(True, 0.08),
                    encoded_cmd=nb(True, 0.10),
                    memory_injection=nb(True, 0.05),
                    external_connection=nb(True, 0.06),
                    suspicious_kernel_module=nb(True, 0.06),
                    suspicious_bash_cmd=nb(True, 0.10),
                    root_process_from_user=nb(True, 0.08),
                    night_creation=random.random() < 0.55,
                    label=1,
                )

            elif s == "lateral":

                row = dict(
                    wrong_parent=random.random() < 0.65,
                    encoded_cmd=random.random() < 0.55,
                    memory_injection=random.random() < 0.40,
                    external_connection=nb(True, 0.06),
                    suspicious_kernel_module=random.random() < 0.25,
                    suspicious_bash_cmd=random.random() < 0.70,
                    root_process_from_user=random.random() < 0.50,
                    night_creation=random.random() < 0.35,
                    label=1,
                )

            elif s == "injection":

                row = dict(
                    wrong_parent=random.random() < 0.70,
                    encoded_cmd=random.random() < 0.65,
                    memory_injection=nb(True, 0.04),
                    external_connection=random.random() < 0.80,
                    suspicious_kernel_module=random.random() < 0.20,
                    suspicious_bash_cmd=random.random() < 0.60,
                    root_process_from_user=random.random() < 0.55,
                    night_creation=random.random() < 0.40,
                    label=1,
                )

            else:

                row = dict(
                    wrong_parent=random.random() < 0.45,
                    encoded_cmd=random.random() < 0.50,
                    memory_injection=random.random() < 0.30,
                    external_connection=random.random() < 0.50,
                    suspicious_kernel_module=random.random() < 0.35,
                    suspicious_bash_cmd=random.random() < 0.55,
                    root_process_from_user=random.random() < 0.40,
                    night_creation=random.random() < 0.30,
                    label=1,
                )

            row["case_id"] = cid
            rows.append(row)

        random.shuffle(rows)

        df = pd.DataFrame(rows)

        df = self._cast_features(df)

        logger.info(

            f"Generated synthetic DataFrame: {len(df)} rows | "
            
            f"malicious: {df['label'].sum()} ({df['label'].mean() * 100:.1f}%)"

        )

        return df

    @staticmethod
    def _cast_features(df: pd.DataFrame) -> pd.DataFrame:

        for col in MEMORY_FEATURE_COLS:

            if col in df.columns:

                df[col] = df[col].astype(int)

        return df