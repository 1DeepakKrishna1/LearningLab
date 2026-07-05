"""
Pattern 09: Learning and Adaptation
=====================================
Concept: The agent maintains a performance model for different strategies. After
each attempt it receives feedback, updates strategy scores, and in the next round
selects the highest-scoring strategy. This demonstrates in-context meta-learning
without fine-tuning.

Graph:  START → select_strategy → generate_answer → evaluate_feedback
                                                           |
                                                   adapt_strategy → END

The graph is invoked per question; strategy_scores persist across calls.

Demo:   6 trivia questions answered using three reasoning strategies
        (confidence-first, evidence-first, elimination-first). Agent adapts
        which strategy to use based on rolling accuracy.
"""
from __future__ import annotations

import traceback
from typing import Annotated, Dict, List
import operator

from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict

from core.base import BasePattern, PatternResult
from core.llm import MODEL_LARGE, MODEL_SMALL

STRATEGY_PROMPTS: Dict[str, str] = {
    "confidence": (
        "Answer using the CONFIDENCE-FIRST approach: immediately state the answer "
        "you are most confident about, then briefly justify it."
    ),
    "evidence": (
        "Answer using the EVIDENCE-FIRST approach: list 2-3 supporting facts or "
        "clues before stating your final answer."
    ),
    "elimination": (
        "Answer using the ELIMINATION approach: identify what the answer is NOT, "
        "narrow down possibilities, then state the most likely answer."
    ),
}

DEMO_QA = [
    ("What is the chemical symbol for gold?", "Au"),
    ("Which planet has the most moons in our solar system?", "Saturn"),
    ("Who wrote the novel '1984'?", "George Orwell"),
    ("What is the speed of light in vacuum (approximate, km/s)?", "300000"),
    ("In what year did the Berlin Wall fall?", "1989"),
    ("What programming language was created by Guido van Rossum?", "Python"),
]


class LearningState(TypedDict):
    question: str
    correct_answer: str
    current_strategy: str
    agent_answer: str
    is_correct: bool
    feedback_notes: str
    strategy_scores: Dict[str, float]        # strategy → rolling accuracy (0.0–1.0)
    strategy_attempts: Dict[str, int]
    adaptation_log: Annotated[List[Dict], operator.add]
    round_number: int


class PatternLearningAdaptation(BasePattern):
    PATTERN_NUMBER = 9
    PATTERN_NAME = "Learning and Adaptation"
    DESCRIPTION = (
        "Agent tracks strategy performance across rounds and adapts to use the best-scoring approach."
    )

    # ------------------------------------------------------------------ nodes

    def _select_strategy(self, state: LearningState) -> dict:
        scores = state["strategy_scores"]
        attempts = state["strategy_attempts"]

        # UCB1-style selection: prefer strategies with fewer attempts (exploration bonus)
        import math
        total_attempts = sum(attempts.values()) or 1
        best_strategy = max(
            scores.keys(),
            key=lambda s: scores[s] + math.sqrt(2 * math.log(total_attempts + 1) / (attempts[s] + 1)),
        )
        return {
            "current_strategy": best_strategy,
            "adaptation_log": [{
                "round": state["round_number"],
                "event": "strategy_selected",
                "strategy": best_strategy,
                "scores": dict(scores),
            }],
        }

    def _generate_answer(self, state: LearningState) -> dict:
        strategy_instruction = STRATEGY_PROMPTS[state["current_strategy"]]
        prompt = (
            f"Question: {state['question']}\n\n"
            f"Strategy: {strategy_instruction}\n\n"
            "Give a concise answer (1-2 sentences max)."
        )
        answer = self.llm.simple_prompt(prompt, model=MODEL_LARGE, max_tokens=150)
        return {
            "agent_answer": answer,
            "adaptation_log": [{
                "round": state["round_number"],
                "event": "answer_generated",
                "strategy": state["current_strategy"],
                "answer_preview": answer[:80],
            }],
        }

    def _evaluate_feedback(self, state: LearningState) -> dict:
        """Check if the agent's answer contains the correct answer."""
        correct = state["correct_answer"].lower()
        agent_ans = state["agent_answer"].lower()
        is_correct = correct in agent_ans or any(
            word in agent_ans for word in correct.split() if len(word) > 3
        )

        prompt = (
            f"Question: {state['question']}\n"
            f"Correct answer: {state['correct_answer']}\n"
            f"Agent's answer: {state['agent_answer']}\n\n"
            "In one sentence, explain what the agent got right or wrong."
        )
        notes = self.llm.simple_prompt(prompt, model=MODEL_SMALL, max_tokens=100)

        return {
            "is_correct": is_correct,
            "feedback_notes": notes,
            "adaptation_log": [{
                "round": state["round_number"],
                "event": "feedback_received",
                "is_correct": is_correct,
                "notes": notes[:100],
            }],
        }

    def _adapt_strategy(self, state: LearningState) -> dict:
        """Update rolling accuracy for the current strategy using exponential moving average."""
        strat = state["current_strategy"]
        alpha = 0.4   # learning rate

        old_score = state["strategy_scores"][strat]
        new_signal = 1.0 if state["is_correct"] else 0.0
        new_score = (1 - alpha) * old_score + alpha * new_signal

        updated_scores = {**state["strategy_scores"], strat: new_score}
        updated_attempts = {**state["strategy_attempts"], strat: state["strategy_attempts"][strat] + 1}

        return {
            "strategy_scores": updated_scores,
            "strategy_attempts": updated_attempts,
            "adaptation_log": [{
                "round": state["round_number"],
                "event": "scores_updated",
                "strategy": strat,
                "old_score": round(old_score, 3),
                "new_score": round(new_score, 3),
            }],
        }

    # --------------------------------------------------------------- graph

    def build_graph(self) -> StateGraph:
        graph = StateGraph(LearningState)

        graph.add_node("select_strategy", self._select_strategy)
        graph.add_node("generate_answer", self._generate_answer)
        graph.add_node("evaluate_feedback", self._evaluate_feedback)
        graph.add_node("adapt_strategy", self._adapt_strategy)

        graph.add_edge(START, "select_strategy")
        graph.add_edge("select_strategy", "generate_answer")
        graph.add_edge("generate_answer", "evaluate_feedback")
        graph.add_edge("evaluate_feedback", "adapt_strategy")
        graph.add_edge("adapt_strategy", END)

        return graph.compile()

    # --------------------------------------------------------------- run

    def run(self, input_data: str, **kwargs) -> PatternResult:
        """Run 6 rounds of Q&A, adapting strategy each round."""
        try:
            app = self.build_graph()

            shared_scores: Dict[str, float] = {s: 0.5 for s in STRATEGY_PROMPTS}
            shared_attempts: Dict[str, int] = {s: 0 for s in STRATEGY_PROMPTS}

            all_rounds = []
            total_elapsed = 0.0
            correct_count = 0

            for i, (question, correct_answer) in enumerate(DEMO_QA):
                initial: LearningState = {
                    "question": question,
                    "correct_answer": correct_answer,
                    "current_strategy": "confidence",
                    "agent_answer": "",
                    "is_correct": False,
                    "feedback_notes": "",
                    "strategy_scores": dict(shared_scores),
                    "strategy_attempts": dict(shared_attempts),
                    "adaptation_log": [],
                    "round_number": i + 1,
                }
                result, elapsed = self._timed_run(app.invoke, initial)
                total_elapsed += elapsed

                # Persist scores across rounds
                shared_scores = result["strategy_scores"]
                shared_attempts = result["strategy_attempts"]
                if result["is_correct"]:
                    correct_count += 1

                all_rounds.append({
                    "round": i + 1,
                    "question": question,
                    "strategy_used": result["current_strategy"],
                    "answer": result["agent_answer"][:100],
                    "correct": result["is_correct"],
                })

            summary = (
                f"Completed {len(DEMO_QA)} rounds. "
                f"Accuracy: {correct_count}/{len(DEMO_QA)} = {correct_count/len(DEMO_QA)*100:.0f}%. "
                f"Final strategy scores: {', '.join(f'{k}={v:.2f}' for k, v in shared_scores.items())}."
            )

            return self._make_result(
                success=True,
                input_data=input_data,
                output_data=summary,
                elapsed_ms=total_elapsed,
                steps=all_rounds,
                metadata={
                    "final_scores": shared_scores,
                    "final_attempts": shared_attempts,
                    "overall_accuracy": correct_count / len(DEMO_QA),
                },
            )
        except Exception:
            return self._make_result(
                success=False,
                input_data=input_data,
                output_data=None,
                error=traceback.format_exc(),
            )
