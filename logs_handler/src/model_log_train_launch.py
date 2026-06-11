import xgboost as xgb
import pandas as pd
import logging
import joblib as jl
import os

class LogModelTrainLaunch():

    MODEL_PATH = f"models/logs_model.pkl"

    def __init__(self , X_train : pd.DataFrame , y_train : pd.Series):

        self.X_train = X_train

        self.y_train = y_train

        self.model = None

        os.makedirs(os.path.dirname(self.MODEL_PATH), exist_ok=True)

        if os.path.exists(self.MODEL_PATH):

            try:

                self.model = jl.load(self.MODEL_PATH)

                logging.info(f"Trained model was loaded at {self.MODEL_PATH}")

            except Exception as e:

                logging.error(e)

        if self.model is None:

            if self.y_train is not None:

                try:

                    self._train_model(X_train , y_train)

                    logging.info(f"Trained model was trained at {self.MODEL_PATH}")

                except Exception as e:

                    logging.error(e)

    def _train_model(self , X_train : pd.DataFrame , y_train : pd.Series) -> None:

        log_model = xgb.XGBClassifier(n_estimators = 200 , max_depth = 10, subsample = 0.8 , random_state = 42)

        try:

            log_model.fit(X_train , y_train)

            self.model = log_model

            jl.dump(log_model, self.MODEL_PATH)

        except Exception as e:

            logging.error(e)

        logging.info(f"Trained model saved at {self.MODEL_PATH}")

    def predict(self , X : pd.DataFrame) -> dict:

        if self.model is None:

            logging.error(f"Trained model was not trained at {self.MODEL_PATH}")

        try:

            preds = self.model.predict(X)

            result = {
                "score" : preds.tolist(),
            }

        except Exception as e:

            logging.error(e)

            result = {"score": None}

        return result

log_model_train_launch = LogModelTrainLaunch()