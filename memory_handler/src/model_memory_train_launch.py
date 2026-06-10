import os
import logging
import joblib as jl
import numpy as np
import pandas as pd
import xgboost as xgb
import shap
from sklearn.metrics import roc_auc_score, classification_report

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


class MemoryModelTrainLaunch:

    MODEL_PATH = "models/memory_model.pkl"

    def __init__(self, X: pd.DataFrame, case_id: pd.Series):

        self.X = X

        self.case_id = case_id

        self.model = None

        self._explainer = None

        try:

            saved = jl.load(MemoryModelTrainLaunch.MODEL_PATH)

            if saved is None:

                try:

                    self._train_model(X=self.X)

                except Exception as e:

                    logger.error(e)

            else:

                self.model      = saved["model"]

                self._explainer = saved["explainer"]

                logger.info(f"Model loaded ← {self.MODEL_PATH}")

        except Exception as e:

            logger.error(e)

    def _train_model(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        X_test: pd.DataFrame | None = None,
        y_test: pd.Series | None = None,
    ) -> None:

        X_clean = self._cast(X[MEMORY_FEATURE_COLS].copy())

        memory_model = xgb.XGBClassifier(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            min_child_weight=3,
            scale_pos_weight=len(y[y == 0]) / max(len(y[y == 1]), 1),
            eval_metric="auc",
            random_state=42,
            verbosity=0,
        )

        eval_set = [(self._cast(X_test[MEMORY_FEATURE_COLS].copy()), y_test)] \
            if X_test is not None and y_test is not None \
            else None

        try:

            memory_model.fit(
                X_clean, y,
                eval_set=eval_set,
                verbose=False,
            )

        except Exception as e:

            logger.error(e)

            return

        self._explainer = shap.TreeExplainer(memory_model)
        self.model = memory_model

        if X_test is not None and y_test is not None:

            X_test_clean = self._cast(X_test[MEMORY_FEATURE_COLS].copy())

            y_prob = memory_model.predict_proba(X_test_clean)[:, 1]

            roc_auc = roc_auc_score(y_test, y_prob)

            report  = classification_report(

                y_test, memory_model.predict(X_test_clean)
            )
            logger.info(f"ROC-AUC on test: {roc_auc:.4f}")

            logger.info(f"\n{report}")

        os.makedirs("models", exist_ok=True)

        jl.dump(

            {"model": memory_model, "explainer": self._explainer},

            self.MODEL_PATH,

        )

        logger.info(f"Trained model saved at {self.MODEL_PATH}")

    def predict(self, X: pd.DataFrame, case_id: pd.Series) -> pd.DataFrame:

        if self.model is None:

            raise RuntimeError(

                "Model not trained. Call _train_model() or provide saved model."

            )

        X_clean = self._cast(X[MEMORY_FEATURE_COLS].copy())

        probas = self.model.predict_proba(X_clean)[:, 1]

        shap_values = self._explainer.shap_values(X_clean)

        result = pd.DataFrame({
            "case_id":      case_id.values,
            "memory_score": np.round(probas, 4),
            "suspicious":   probas >= 0.40,
        })

        for i, col in enumerate(MEMORY_FEATURE_COLS):

            result[f"shap_{col}"] = np.round(shap_values[:, i], 4)

        return result

    @staticmethod
    def _cast(X: pd.DataFrame) -> pd.DataFrame:

        for col in MEMORY_FEATURE_COLS:

            if col in X.columns:

                X[col] = X[col].astype(int)

        return X.astype("float32")