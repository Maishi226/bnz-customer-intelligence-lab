import importlib.util
from pathlib import Path


def invoke_handler():
    path = Path(__file__).parent / "lambda" / "lex_fulfillment.py"
    spec = importlib.util.spec_from_file_location("lex_fulfillment", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    module._bedrock_answer = lambda *_args: (_ for _ in ()).throw(
        RuntimeError("Bedrock disabled in unit test")
    )
    return module.handler(
        {
            "inputTranscript": "Why is this risky?",
            "sessionState": {
                "intent": {"name": "CampaignAdvisor"},
                "sessionAttributes": {
                    "simulationContext": '{"selected_campaign":{"risk_level":"Medium","scores":{"readiness":72}},"portfolio_summary":{"top_risks":["fees need prominence"]}}'
                },
            },
        },
        None,
    )
