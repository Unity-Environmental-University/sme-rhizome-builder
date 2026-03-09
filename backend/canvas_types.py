"""
Canvas API types — typed with alkahest phases.

Fluid types: stable but can re-flow if the Canvas API shifts.
Pin the fields we use, let a future decohere fill in the rest.
"""

from dataclasses import dataclass
from alkahest import Fluid


@dataclass
class CanvasCourse(Fluid):
    id: int
    name: str
    course_code: str


@dataclass
class CanvasAssignment(Fluid):
    id: int
    name: str
    points_possible: float | None
    html_url: str
    has_rubric: bool = False


@dataclass
class CanvasPushResult(Fluid):
    assignment_id: str
    html_url: str
    course_id: str
