import pytest


@pytest.fixture(params=["durable_rules", "drools"])
def rules_engine(request):
    return {"EDA_RULES_ENGINE": request.param}
