from langsmith import wrappers
from openai import OpenAI
from pydantic import BaseModel

oai_client = wrappers.wrap_openai(OpenAI())


class ReportEvalResponse(BaseModel):
    score: int
    reasoning: str


def report_quality_evaluator(inputs: dict, outputs) -> dict:
    """
    Judge if the generated report:
    1. Covers required sections.
    2. Includes tariff simulation and charts (placeholders [[FIGURE:...]]).
    3. Is clear and professional.
    Returns a score (1-5) and reasoning.
    """
    # Build task summary string
    task = (
            inputs.get("task")
            or f"{inputs.get('manufacturer', '')} {inputs.get('model', '')} {inputs.get('component', '')} supply chain"
    )

    # Handle output type (string or dict)
    report = outputs if isinstance(outputs, str) else outputs.get("draft", "")

    instructions = """
    You are an expert automotive supply chain analyst.
    Given the task and generated report, score it from 1 to 5 based on:
    - Completeness (all required sections included)
    - Accuracy (simulation and chart references present if required)
    - Clarity and professional tone
    Provide reasoning for your score.
    """

    msg = f"Task: {task}\nReport:\n{report}"
    response = oai_client.beta.chat.completions.parse(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": instructions},
            {"role": "user", "content": msg},
        ],
        response_format=ReportEvalResponse
    )

    parsed = response.choices[0].message.parsed
    return {"score": parsed.score, "reasoning": parsed.reasoning}