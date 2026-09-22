"""Predictor registry — add new models here without changing the daily job loop."""
from predictor1 import predict_item

# Stable ids stored in predictions.predictor; values are callables
# matching predict_item(records, item_name, horizon=1) -> PredictionResult
PREDICTORS = {
    "weighted_linear_trend": predict_item,
}

DEFAULT_PREDICTOR = next(iter(PREDICTORS))

def listPredictorIds():
    return list(PREDICTORS.keys())

def isValidPredictor(predictorId: str) -> bool:
    return predictorId in PREDICTORS

def formatPredictorLabel(predictorId: str) -> str:
    return predictorId.replace("_", " ").title()
