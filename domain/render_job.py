from dataclasses import dataclass, field
from uuid import uuid4


@dataclass(slots=True)
class RenderJob:
    project_id: str
    preset: str
    job_id: str = field(default_factory=lambda: str(uuid4()))
    output_path: str | None = None
