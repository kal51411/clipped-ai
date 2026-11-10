"""
Clipped-AI — ORM Models Package
Import all models here so SQLAlchemy discovers them on startup.
"""
from app.models.user import User
from app.models.project import Project
from app.models.video import Video
from app.models.transcript import Transcript
from app.models.job import Job
from app.models.clip import Clip
from app.models.editing_project import EditingProject

__all__ = [
    "User",
    "Project",
    "Video",
    "Transcript",
    "Job",
    "Clip",
    "EditingProject",
]
