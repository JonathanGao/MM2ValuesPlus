"""Predictor registry — add new models here without changing the daily job loop."""
from predictor1 import predict_item
from .ml_forest import predict_item as predict_ml_item

# Stable ids stored in predictions.predictor; values are callables
# matching predict_item(records, item_name, horizon=1) -> PredictionResult.
# The linear model stays first so it remains the default.
PREDICTORS = {
    "weighted_linear_trend": predict_item,
    "random_forest_direct": predict_ml_item,
}

DEFAULT_PREDICTOR = next(iter(PREDICTORS))

def listPredictorIds():
    return list(PREDICTORS.keys())

def isValidPredictor(predictorId: str) -> bool:
    return predictorId in PREDICTORS

def formatPredictorLabel(predictorId: str) -> str:
    return predictorId.replace("_", " ").title()
