from typing import TypedDict, Dict, List, Optional
from typing_extensions import Annotated
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages

class SharedState(TypedDict, total=False):
    messages: Annotated[List[AnyMessage], add_messages]

    db_content: Annotated[List[AnyMessage], add_messages]
    articles_path: str
    parts_path: str
    plan: str

    chart_spec: Dict[str, str]          # {"chart_id","chart_description","chart_figure_caption"}
    chart_code: str
    chart_generation_success: Optional[bool]
    chart_generation_error: str
    chart_retry_count: int
    chart_metadata: Dict[str, str]