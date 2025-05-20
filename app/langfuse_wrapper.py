"""
A wrapper for langfuse to handle API compatibility issues between versions.
"""

class LangfuseWrapper:
    """
    Wrapper for langfuse callback handlers that works with any version.
    This handles the compatibility issues with different langfuse versions.
    """
    
    def __init__(self, handler=None):
        """Initialize with an optional langfuse handler."""
        self.handler = handler
    
    def log_event(self, name, input=None, output=None):
        """Log an event, compatible with any langfuse version."""
        if self.handler is None:
            # Just print to console if no handler is available
            print(f"[LANGFUSE] Event: {name}, Input: {input}, Output: {output}")
            return
            
        # Try different API versions
        try:
            # First try the old API directly
            if hasattr(self.handler, 'log_event'):
                try:
                    self.handler.log_event(name=name, input=input, output=output)
                    return
                except Exception as e:
                    print(f"[LANGFUSE] log_event error: {e}")
                
            # Try the newer API
            if hasattr(self.handler, 'on_llm_start'):
                try:
                    # Generate a simple run_id if needed
                    import uuid
                    run_id = str(uuid.uuid4())
                    
                    # Try with run_id
                    # Provide a richer serialized dict so Langfuse can parse the LLM model name
                    from config import config
                    serialized = {
                        "id": "ollama-llm",
                        "model": getattr(config.ollama, "llm_model", "unknown"),
                        "model_name": getattr(config.ollama, "llm_model", "unknown"),
                        "type": "ollama",
                        "base_url": getattr(config.ollama, "base_url", ""),
                        "kwargs": {
                            "model": getattr(config.ollama, "llm_model", "unknown"),
                            "base_url": getattr(config.ollama, "base_url", "")
                        }
                    }
                    # Patch: Always provide invocation_params in kwargs (even if empty)
                    kwargs = {"invocation_params": {}}
                    self.handler.on_llm_start(
                        serialized=serialized,
                        prompts=[str(input)] if input is not None else [""],
                        name=name,
                        run_id=run_id,
                        metadata={"output": output} if output is not None else {},
                        **kwargs
                    )
                    
                    if hasattr(self.handler, 'on_llm_end'):
                        # Patch: Provide a dummy response object with .generations attribute
                        class DummyGeneration:
                            def __init__(self, text):
                                self.text = text
                                self.generation_info = None
                        class DummyLLMResult:
                            generations = [[DummyGeneration(str(output) if output is not None else "")]]
                            llm_output = None
                        self.handler.on_llm_end(response=DummyLLMResult(), run_id=run_id)
                    return
                except TypeError as e:
                    # Try without run_id if there's a TypeError
                    try:
                        self.handler.on_llm_start(
                            serialized={},
                            prompts=[str(input)] if input is not None else [""],
                            name=name,
                            metadata={"output": output} if output is not None else {}
                        )
                        
                        if hasattr(self.handler, 'on_llm_end'):
                            self.handler.on_llm_end({})
                        return
                    except Exception as e2:
                        print(f"[LANGFUSE] on_llm_start fallback error: {e2}")
                except Exception as e:
                    print(f"[LANGFUSE] on_llm_start error: {e}")
                
            # If we get here, none of the APIs worked, so log to console
            print(f"[LANGFUSE] Warning: Could not find compatible API. Event: {name}")
            
        except Exception as e:
            # Catch all exceptions and print to console
            print(f"[LANGFUSE] Error: {e}. Event: {name}")
