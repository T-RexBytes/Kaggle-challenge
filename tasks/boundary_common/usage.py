"""Token metering across the whole tool loop.

kaggle_benchmarks runs tool rounds in a forked chat, so chat.usage on the
outer chat misses them. This listens to every new assistant message instead.
Values stay None when the provider reports no usage (never silently zero).
"""

from contextlib import contextmanager

from kaggle_benchmarks import events


class UsageMeter:
    def __init__(self):
        self.model_turns = 0
        self.input_tokens: int | None = None
        self.output_tokens: int | None = None
        self.cost_nanodollars: int | None = None

    def new_message(self, chat, message) -> None:  # event hook
        if getattr(message.sender, "role", None) != "assistant":
            return
        self.model_turns += 1
        usage = message.usage
        self.input_tokens = _add(self.input_tokens, usage.input_tokens)
        self.output_tokens = _add(self.output_tokens, usage.output_tokens)
        self.cost_nanodollars = _add(self.cost_nanodollars, usage.total_cost_nanodollars)

    def as_dict(self) -> dict:
        return {
            "model_turns": self.model_turns,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cost_nanodollars": self.cost_nanodollars,
        }


def _add(total, value):
    if value is None:
        return total
    return (total or 0) + value


@contextmanager
def meter_usage():
    meter = UsageMeter()
    events.manager.bind(meter)
    try:
        yield meter
    finally:
        events.manager.unbind(meter)
