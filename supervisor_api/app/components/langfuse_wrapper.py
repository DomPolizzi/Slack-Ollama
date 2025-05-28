"""
Wrapper for Langfuse to handle API compatibility issues and trace graph execution.
"""

import uuid
from typing import Any
from configs.config import config
from langfuse.callback import CallbackHandler

class LangfuseWrapper:
    def __init__(self):
        # Initialize Langfuse handler if keys are present
        if config.langfuse.public_key and config.langfuse.secret_key:
            self.handler = CallbackHandler(
                public_key=config.langfuse.public_key,
                secret_key=config.langfuse.secret_key,
                host=config.langfuse.host
            )
        else:
            self.handler = None

    def session_start(self, graph_name: str, input: dict):
        run_id = str(uuid.uuid4())
        if self.handler and hasattr(self.handler, "on_session_start"):
            self.handler.on_session_start(name=graph_name, run_id=run_id, input=input)
        else:
            print(f"[LANGFUSE] session_start {graph_name} run_id={run_id} input={input}")
        return run_id

    def log_event(self, name: str, input: Any = None, output: Any = None, run_id: str = None):
        if self.handler and hasattr(self.handler, "log_event"):
            self.handler.log_event(name=name, input=input, output=output, run_id=run_id)
        else:
            print(f"[LANGFUSE] event {name} input={input} output={output} run_id={run_id}")

    def session_end(self, graph_name: str, output: dict, run_id: str = None):
        if self.handler and hasattr(self.handler, "on_session_end"):
            self.handler.on_session_end(name=graph_name, run_id=run_id, output=output)
        else:
            print(f"[LANGFUSE] session_end {graph_name} run_id={run_id} output={output}")