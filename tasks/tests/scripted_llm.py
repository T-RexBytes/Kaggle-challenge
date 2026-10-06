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

    def __init__(self, steps: list[list[dict]], final: str, name: str = "scripted/test-model", usage: dict | None = None, fail_with: list[Exception] | None = None):
        super().__init__(name=name)
        self.model = name
        self.steps = steps
        self.final = final
        self.turn = 0
        self.usage = usage or {}
        self.fail_with = list(fail_with or [])  # raised one per invoke, before the script runs
        self.calls: list[dict] = []

    def invoke(self, messages, system=None, reasoning=None, tools=None, **kwargs):
        self.calls.append({
            "reasoning": reasoning,
            "max_completion_tokens": kwargs.get("max_completion_tokens"),
            "n_user_messages": sum(1 for m in messages if getattr(m.sender, "role", None) == "user"),
        })
        if self.fail_with:
            raise self.fail_with.pop(0)
        if self.turn < len(self.steps):
            calls = self.steps[self.turn]
            self.turn += 1
            return LLMResponse(content="", tool_calls=calls, meta=dict(self.usage))
        return LLMResponse(content=self.final, meta=dict(self.usage))


class TextScriptedLLM(ScriptedLLM):
    """Replies with plain text (no native tool calls), one reply per turn.

    If the request carries native tools and `rejects_native` is set, it raises
    the given errors first, like gpt-6-astra does on the Kaggle proxy.
    """

    def __init__(self, replies: list[str], rejects_native: list[Exception] | None = None, **kw):
        super().__init__([], replies[-1] if replies else "", **kw)
        self.replies = list(replies)
        self.rejects_native = list(rejects_native or [])

    def invoke(self, messages, system=None, reasoning=None, tools=None, **kwargs):
        self.calls.append({"reasoning": reasoning, "tools": bool(tools),
                           "max_completion_tokens": kwargs.get("max_completion_tokens")})
        if tools and self.rejects_native:
            raise self.rejects_native.pop(0)
        if tools:
            raise AssertionError("text model got native tools after its errors ran out")
        reply = self.replies.pop(0) if self.replies else self.final
        return LLMResponse(content=reply, meta=dict(self.usage))
