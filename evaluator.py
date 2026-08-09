"""
Compatibility shim forwarding imports to agents.evaluator.
"""

from agents.evaluator import AnswerEvaluation, AnswerEvaluator, DimensionalScore

__all__ = ["AnswerEvaluation", "AnswerEvaluator", "DimensionalScore"]