import pytest


@pytest.fixture(params=["durable_rules", "drools"])
def rules_engine(request):
    return {"EDA_RULES_ENGINE": request.param}


@pytest.fixture(scope="session")
def default_rules_engine():
    return {"EDA_RULES_ENGINE": "drools"}
