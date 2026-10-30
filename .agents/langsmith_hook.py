#!/usr/bin/env python3
"""Antigravity Stop Hook to log conversation turns and tool calls to LangSmith."""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys

from dotenv import load_dotenv
from langsmith.run_trees import RunTree


def parse_iso(ts: str | None) -> datetime:
    if not ts:
        return datetime.now(timezone.utc)
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return datetime.now(timezone.utc)


def extract_user_request(raw_content: str) -> str:
    match = re.search(
        r"<USER_REQUEST>\s*(.*?)\s*</USER_REQUEST>", raw_content, re.DOTALL
    )
    if match:
        return match.group(1).strip()
    return raw_content.strip()


def resolve_transcript_path(
    payload: dict,
) -> Path | None:
    raw_path = payload.get("transcriptPath")
    candidates = []
    if raw_path:
        p = Path(raw_path)
        candidates.append(p.with_name("transcript_full.jsonl"))
        candidates.append(p)

    conv_id = payload.get("conversationId")
    if conv_id:
        for app_dir in ("antigravity-cli", "antigravity", "antigravity-ide"):
            base = (
                Path.home()
                / ".gemini"
                / app_dir
                / "brain"
                / conv_id
                / ".system_generated"
                / "logs"
            )
            candidates.append(base / "transcript_full.jsonl")
            candidates.append(base / "transcript.jsonl")

    for c in candidates:
        if c.is_file():
            return c
    return None


def main() -> None:
    # Load .env from project root
    project_root = Path(__file__).resolve().parent.parent
    load_dotenv(project_root / ".env")

    try:
        raw_stdin = sys.stdin.read().strip()
        payload = json.loads(raw_stdin) if raw_stdin else {}
    except Exception:
        payload = {}

    if not os.getenv("LANGSMITH_API_KEY") and not os.getenv("LANGCHAIN_API_KEY"):
        print(json.dumps({"decision": "stop"}))
        return

    transcript_path = resolve_transcript_path(payload)
    if not transcript_path:
        print(json.dumps({"decision": "stop"}))
        return

    try:
        steps = [
            json.loads(line)
            for line in transcript_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    except Exception as exc:
        sys.stderr.write(f"Failed to read transcript: {exc}\n")
        print(json.dumps({"decision": "stop"}))
        return

    # Find the latest explicit user input step
    last_user_pos = None
    for idx in range(len(steps) - 1, -1, -1):
        if steps[idx].get("type") == "USER_INPUT":
            last_user_pos = idx
            break

    if last_user_pos is None:
        print(json.dumps({"decision": "stop"}))
        return

    turn_steps = steps[last_user_pos:]
    user_step = turn_steps[0]
    turn_id = user_step.get("step_index", last_user_pos)
    last_step_idx = turn_steps[-1].get("step_index", len(steps) - 1)

    # Avoid duplicate logging of the exact same turn state
    state_file = transcript_path.parent / "langsmith_traced_state.json"
    try:
        if state_file.is_file():
            state = json.loads(state_file.read_text(encoding="utf-8"))
            if (
                state.get("turn_id") == turn_id
                and state.get("last_step_idx") == last_step_idx
            ):
                print(json.dumps({"decision": "stop"}))
                return
    except Exception:
        pass

    project_name = os.getenv("LANGSMITH_PROJECT", "antigravity-traces")
    conv_id = payload.get("conversationId", "unknown")
    model_name = payload.get("modelName") or "antigravity"
    user_query = extract_user_request(user_step.get("content", ""))

    # Find final assistant response
    final_output = ""
    for s in reversed(turn_steps):
        if s.get("type") == "PLANNER_RESPONSE" and s.get("content"):
            final_output = s["content"]
            break

    start_time = parse_iso(user_step.get("created_at"))
    end_time = parse_iso(turn_steps[-1].get("created_at"))

    try:
        parent_run = RunTree(
            name="Antigravity Agent Turn",
            run_type="chain",
            project_name=project_name,
            inputs={"input": user_query},
            start_time=start_time,
            extra={
                "metadata": {
                    "conversation_id": conv_id,
                    "thread_id": conv_id,
                    "model": model_name,
                    "turn_step_index": turn_id,
                }
            },
        )
        parent_run.post()

        i = 1
        while i < len(turn_steps):
            step = turn_steps[i]
            if step.get("type") == "PLANNER_RESPONSE":
                step_start = parse_iso(step.get("created_at"))
                tool_calls = step.get("tool_calls") or []

                # Advance through subsequent GENERIC steps corresponding to tool outputs
                tool_results = []
                j = i + 1
                while (
                    j < len(turn_steps)
                    and turn_steps[j].get("type") == "GENERIC"
                    and len(tool_results) < len(tool_calls)
                ):
                    tool_results.append(turn_steps[j])
                    j += 1

                step_end = (
                    parse_iso(tool_results[-1].get("created_at"))
                    if tool_results
                    else parse_iso(
                        turn_steps[i + 1].get("created_at")
                        if i + 1 < len(turn_steps)
                        else step.get("created_at")
                    )
                )

                in_tok = step.get("input_tokens", 0) + step.get("cache_read_tokens", 0)
                out_tok = step.get("output_tokens", 0)

                llm_child = parent_run.create_child(
                    name=f"Planner ({model_name})",
                    run_type="llm",
                    inputs={"step_index": step.get("step_index")},
                    start_time=step_start,
                    extra={
                        "metadata": {
                            "input_tokens": step.get("input_tokens", 0),
                            "cache_read_tokens": step.get("cache_read_tokens", 0),
                            "output_tokens": out_tok,
                        }
                    },
                )
                llm_child.post()
                llm_child.end(
                    outputs={
                        "content": step.get("content", ""),
                        "thinking": step.get("thinking", ""),
                        "tool_calls": tool_calls,
                        "usage_metadata": {
                            "input_tokens": in_tok,
                            "output_tokens": out_tok,
                            "total_tokens": in_tok + out_tok,
                        },
                    },
                    end_time=step_end,
                )
                llm_child.patch()

                for idx_tc, tc in enumerate(tool_calls):
                    res_step = (
                        tool_results[idx_tc] if idx_tc < len(tool_results) else {}
                    )
                    tc_end = parse_iso(
                        res_step.get("created_at") or step.get("created_at")
                    )
                    tool_child = parent_run.create_child(
                        name=tc.get("name", "tool"),
                        run_type="tool",
                        inputs=tc.get("args", {}),
                        start_time=step_start,
                    )
                    tool_child.post()
                    tool_child.end(
                        outputs={"output": res_step.get("content", "")},
                        error=(
                            res_step.get("error")
                            if res_step.get("status") == "ERROR"
                            else None
                        ),
                        end_time=tc_end,
                    )
                    tool_child.patch()

                i = j
            else:
                i += 1

        parent_run.end(outputs={"output": final_output}, end_time=end_time)
        parent_run.patch()

        state_file.write_text(
            json.dumps({"turn_id": turn_id, "last_step_idx": last_step_idx}),
            encoding="utf-8",
        )
    except Exception as exc:
        sys.stderr.write(f"LangSmith trace error: {exc}\n")

    print(json.dumps({"decision": "stop"}))


if __name__ == "__main__":
    main()
