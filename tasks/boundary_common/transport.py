"""Transport-layer fallbacks for API constraints that are not model behaviour.

Rulebook section 26: model-specific differences stay at the transport layer and
never change the objective, environment or scoring. Each fallback fires only on
a known API error, so models that already work keep default settings. Every
fallback that fires is written to the run record.

Known constraints (seen on the Kaggle Model Proxy):
- Some OpenAI reasoning models reject function tools while a reasoning_effort
  is active on the chat endpoint ("set reasoning_effort to 'none'").
- Some of those also reject reasoning_effort 'none' (gpt-6-astra, gpt-6.1-sol),
  so native function tools cannot work at all. They fall back to a text tool
  protocol: same tools, same sandbox, the call is written as JSON in the reply.
- The proxy reserves quota for the largest possible output, so a model with a
  large default output limit can be refused ("set max_output_tokens ...").
"""

import inspect
import json
import os
import re

OUTPUT_CAP_TOKENS = 4096  # far above what any T01-style answer needs
MAX_TEXT_TOOL_ROUNDS = 12


def fallback_for(exc: Exception, applied: dict) -> tuple[str, dict, tuple] | None:
    """Return (reason, keys to set, keys to drop) for a known constraint, else None."""
    # Proxy errors arrive as a repr of a dict holding a JSON string, so quotes come
    # escaped, e.g. \'none\'. Strip quotes and backslashes before matching.
    text = re.sub(r"[\\'\"]", "", str(exc).lower())
    text_mode = applied.get("tool_protocol") == "text"
    if "reasoning_effort" in text and "does not support none" in text and not text_mode:
        return "native_tools_impossible_use_text_protocol", {"tool_protocol": "text"}, ("reasoning",)
    if "function tools" in text and "reasoning_effort" in text and not text_mode and "reasoning" not in applied:
        return "tools_need_reasoning_none", {"reasoning": "none"}, ()
    if "tool" in text and ("not supported" in text or "unsupported" in text) and not text_mode:
        return "native_tools_unsupported_use_text_protocol", {"tool_protocol": "text"}, ("reasoning",)
    if "max_output_tokens" in text and "quota" in text and "extra_api_params" not in applied:
        return "quota_reservation_needs_output_cap", {
            "extra_api_params": {"max_completion_tokens": OUTPUT_CAP_TOKENS}
        }, ()
    return None


def initial_overrides() -> dict:
    """BOUNDARY_FORCE_TEXT_TOOLS=1 forces the text protocol (local testing only)."""
    return {"tool_protocol": "text"} if os.environ.get("BOUNDARY_FORCE_TEXT_TOOLS") == "1" else {}


def run_with_fallbacks(attempt, acted, max_attempts: int = 5):
    """Run attempt(call_kwargs); on a known API constraint, retry with a fix.

    `acted()` must say whether the failed attempt already caused tool activity.
    A half-finished attempt is never replayed, because that would hide what the
    model already did. Returns (result, applied_changes, fallback_log).
    """
    applied: dict = initial_overrides()
    log: list[dict] = []
    for n in range(1, max_attempts + 1):
        try:
            return attempt(dict(applied)), dict(applied), log
        except Exception as exc:  # noqa: BLE001 - re-raised unless a known constraint
            change = None if acted() else fallback_for(exc, applied)
            if change is None or n == max_attempts:
                raise
            reason, update, drop = change
            for key in drop:
                applied.pop(key, None)
            applied.update(update)
            log.append({"attempt": n, "reason": reason, "error": str(exc)[:300]})


# -- text tool protocol --------------------------------------------------------


def describe_tools(tools) -> str:
    lines = []
    for tool in tools:
        params = ", ".join(
            f"{p.name}: {getattr(p.annotation, '__name__', 'str')}"
            + ("" if p.default is inspect.Parameter.empty else f" = {p.default!r}")
            for p in inspect.signature(tool).parameters.values()
        )
        lines.append(f"- {tool.__name__}({params}): {(tool.__doc__ or '').strip()}")
    return "\n".join(lines)


TEXT_PROTOCOL = """

How to use the tools: to call a tool, reply with only one JSON object and nothing else, for example
{{"tool": "list_dir", "arguments": {{"path": "."}}}}
You will get the tool result in the next message. Call one tool per reply.
When you are finished, reply with your final answer as plain text, without JSON.

Tools:
{tools}"""


def parse_tool_call(reply: str) -> dict | None:
    """Return {"tool", "arguments"} if the reply is a tool call, else None."""
    if not reply:
        return None
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", reply.strip())
    start = text.find("{")
    if start < 0:
        return None
    try:
        obj, _ = json.JSONDecoder().raw_decode(text[start:])
    except ValueError:
        return None
    if not isinstance(obj, dict) or not isinstance(obj.get("tool"), str):
        return None
    args = obj.get("arguments", {})
    return {"tool": obj["tool"], "arguments": args if isinstance(args, dict) else {}}


def native_rounds_supported() -> bool:
    """True when LLMChat.prompt forwards extra_api_params into native_tool_agent (SDK 0.6.x).

    On an SDK that does not, max_tool_rounds would reach the model API, so it is not sent.
    """
    try:
        from kaggle_benchmarks.actors.llms import LLMChat
        from kaggle_benchmarks.tools.native import native_tool_agent

        source = inspect.getsource(LLMChat.prompt)
        return ("max_tool_rounds" in inspect.signature(native_tool_agent).parameters
                and "native_tool_agent(" in source and "**extra" in source)
    except Exception:  # noqa: BLE001 - unknown SDK layout: keep the SDK default
        return False


def text_tool_agent(llm, prompt: str, tools, rounds: int | None = None, **prompt_kwargs) -> str:
    """Tool loop without native function calling. Returns the final reply."""
    by_name = {t.__name__: t for t in tools}
    message = prompt + TEXT_PROTOCOL.format(tools=describe_tools(tools))
    rounds = rounds or MAX_TEXT_TOOL_ROUNDS
    for _ in range(rounds):
        reply = llm.prompt(message, **prompt_kwargs)
        call = parse_tool_call(reply)
        if call is None:
            return reply
        tool = by_name.get(call["tool"])
        if tool is None:
            result = f"Error: unknown tool {call['tool']!r}. Tools: {', '.join(by_name)}"
        else:
            try:
                result = tool(**call["arguments"])
            except Exception as exc:  # noqa: BLE001 - reported back like a native tool error
                result = f"Error invoking tool {call['tool']!r}: {exc}"
        message = f"Tool result for {call['tool']}:\n{result}"
    raise RuntimeError(f"Text tool round limit of {rounds} exhausted")


def prompt_with_tools(llm, prompt: str, tools, call_kwargs: dict, rounds: int | None = None) -> str:
    """Native tool calling by default; the text protocol when a fallback chose it.

    rounds: tool-round budget for this task (None keeps the defaults: SDK 10, text 12).
    """
    kwargs = {k: v for k, v in call_kwargs.items() if k != "tool_protocol"}
    if call_kwargs.get("tool_protocol") == "text":
        return text_tool_agent(llm, prompt, tools, rounds=rounds, **kwargs)
    if rounds and native_rounds_supported():
        kwargs["extra_api_params"] = {**kwargs.get("extra_api_params", {}), "max_tool_rounds": rounds}
    return llm.prompt(prompt, tools=tools, **kwargs)
