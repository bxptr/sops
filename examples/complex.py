from __future__ import annotations

import json
import os
from typing import Literal

import sops


def main() -> None:
    """
    This example shows a pattern where Python controls the loop and the LM controls
    typed state transitions each step.

    The key behavior is not just "ask one prompt": we keep an evolving typed state
    object, branch with c(), generate typed subplans with a(), and refine strategy
    with f()+o() until a stopping condition is met.
    """
    model = os.getenv("SOPS_MODEL", "gpt-5.2")
    sops.backend = sops.openai(model=model)

    objective = "Design a realistic 10-day launch plan for a small note-taking app."
    constraints = [
        "2 engineers + 1 designer",
        "No paid ads",
        "Budget <= $5,000",
        "Must show measurable traction by day 10",
    ]

    # Initial typed state.
    state = sops.f(
        f"""
        Build an initial execution state.
        Objective: {objective}
        Constraints: {constraints}
        """,
        sops.o(
            {
                "plan_name": str,
                "north_star_metric": str,
                "risks": [str],
                "assumptions": [str],
                "day_1_actions": [str],
                "confidence": float,
            }
        ),
    )

    max_rounds = 4
    round_no = 1
    history: list[dict[str, object]] = []

    while round_no <= max_rounds:
        # Generate a typed decision update.
        update = sops.f(
            f"""
            You are running an adaptive planning loop.
            Objective: {objective}
            Constraints: {constraints}
            Current state:
            {json.dumps(state, indent=2)}

            Return a state update that improves realism.
            """,
            sops.o(
                {
                    "focus": Literal["distribution", "messaging", "product", "measurement"],
                    "changes": [str],
                    "new_risks": [str],
                    "confidence_delta": float,
                    "should_pivot": bool,
                }
            ),
        )

        history.append(update)

        state["risks"] = sorted({*state["risks"], *update["new_risks"]})
        state["confidence"] = max(0.0, min(1.0, state["confidence"] + update["confidence_delta"]))

        # Generate typed micro-tasks for this round.
        tasks = sops.a(
            f"""
            Generate 3 concrete tasks for round {round_no}
            focused on: {update["focus"]}.
            Constraints: {constraints}
            """,
            str,
        )

        # Use LM-powered boolean branching.
        done = sops.c(
            f"""
            Stop condition:
            - confidence >= 0.78
            - no critical unresolved risk remains
            - there is at least one concrete measurement task

            Current confidence: {state["confidence"]}
            Current risks: {state["risks"]}
            Current tasks: {tasks}
            Should we stop now?
            """
        )

        print(f"\nRound {round_no}")
        print("Focus:", update["focus"])
        print("Tasks:", tasks)
        print("Confidence:", state["confidence"])
        print("Stop:", done)

        if done:
            break
        round_no += 1

    final_report = sops.f(
        f"""
        Produce a final plan memo.
        Objective: {objective}
        Constraints: {constraints}
        Final state:
        {json.dumps(state, indent=2)}
        Update history:
        {json.dumps(history, indent=2)}
        """,
    )

    print("\n===== FINAL MEMO =====\n")
    print(final_report)


if __name__ == "__main__":
    main()
