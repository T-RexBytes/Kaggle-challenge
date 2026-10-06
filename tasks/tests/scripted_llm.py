"""A fake model that follows a fixed script, for offline tests (no quota used).

It goes through the real kaggle_benchmarks tool-calling loop, so the tests
exercise the same path a hosted model would.
"""

from kaggle_benchmarks.actors.llms import LLMChat, LLMResponse


def call(name: str, **arguments) -> dict:
    return {"id": f"call-{name}", "function": {"name": name, "arguments": arguments}}


class ScriptedLLM(LLMChat):
    """`steps` is a list of tool-call lists, one list per model turn.

    After the steps run out the model replies with `final`.
    """

    def __init__(self, steps: list[list[dict]], final: str, name: str = "scripted/test-model", usage: dict | None = None):
        super().__init__(name=name)
        self.model = name
        self.steps = steps
        self.final = final
        self.turn = 0
        self.usage = usage or {}

    def invoke(self, messages, system=None, reasoning=None, tools=None, **kwargs):
        if self.turn < len(self.steps):
            calls = self.steps[self.turn]
            self.turn += 1
            return LLMResponse(content="", tool_calls=calls, meta=dict(self.usage))
        return LLMResponse(content=self.final, meta=dict(self.usage))
