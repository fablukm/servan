"""Prompt builders shared by the voter backends. Deterministic, no model state."""
from __future__ import annotations

Messages = list[dict[str, str]]


def vote_messages(agent: str, lane: str, proposal: str,
                  objection_digest: str | None) -> Messages:
    system = (f"You are the {agent} on a design council. Your lane is {lane}: raise "
              "blocking objections only inside your lane. Answer with JSON matching the "
              "Vote schema exactly.")
    user = f"Proposal:\n{proposal}"
    if objection_digest is not None:
        user += (f"\n\nAnonymized blocking objections from the previous round:\n"
                 f"{objection_digest}")
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def revise_messages(proposal: str, blocking_digest: str) -> Messages:
    system = ("You are the architect-editor of a design council. Revise the proposal to "
              "resolve every blocking objection. Return only the revised proposal text.")
    user = f"Proposal:\n{proposal}\n\nBlocking objections:\n{blocking_digest}"
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def boss_messages(topic: str, unresolved: tuple[str, ...]) -> Messages:
    system = ("You are the boss of a deadlocked design council. Formulate the single "
              "question a human must answer to unblock the council. Return only the question.")
    claims = "\n".join(f"- {claim}" for claim in unresolved)
    user = f"Topic: {topic}\nUnresolved objections:\n{claims}"
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]
