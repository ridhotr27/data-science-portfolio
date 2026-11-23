import pandas as pd
import pytest

from app.ml import analyze, suggest_problem, train, validate_training


def config():
    return {"test_size":.2,"random_seed":42,"shuffle":True,"stratify":True,"numeric_missing":"median","categorical_missing":"most_frequent","encoding":"onehot","scaling":"none","n_estimators":20,"learning_rate":.1,"max_depth":3,"subsample":.8,"colsample_bytree":.8,"min_child_weight":1,"gamma":0,"reg_alpha":0,"reg_lambda":1,"tuning":"none"}


def test_detects_problem_types():
    assert suggest_problem(pd.Series([0,1,0,1]))["type"] == "binary_classification"
    assert suggest_problem(pd.Series(range(100)))["type"] == "regression"


def test_analysis_suggests_identifier():
    cols, summary = analyze(pd.DataFrame({"user_id":range(12),"x":[1,2]*6}))
    assert cols[0]["likely_id"] is True
    assert summary["rows"] == 12


def test_feature_target_validation():
    df=pd.DataFrame({"x":range(20),"y":[0,1]*10})
    with pytest.raises(ValueError): validate_training(df,"y",["y"],"binary_classification")


def test_classification_and_regression_training():
    cls=pd.DataFrame({"x":range(60),"group":["a","b","c"]*20,"y":[0,1]*30})
    trained,_,_=train(cls,"y",["x","group"],"binary_classification",config())
    assert "accuracy" in trained.metrics
    reg=pd.DataFrame({"x":range(60),"y":[v*2+.5 for v in range(60)]})
    trained,_,_=train(reg,"y",["x"],"regression",{**config(),"stratify":False})
    assert "rmse" in trained.metrics
