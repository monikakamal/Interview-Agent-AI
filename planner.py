"""
Compatibility shim forwarding imports to agents.planner.
"""

from agents.planner import InterviewPlan, InterviewPlanner, PlannedQuestion

__all__ = ["InterviewPlan", "InterviewPlanner", "PlannedQuestion"]