import sys
from pathlib import Path

project_home = str(Path(__file__).resolve().parent.parent)
if project_home not in sys.path:
    sys.path = [project_home] + sys.path

from app.factory import create_app

application = create_app()
