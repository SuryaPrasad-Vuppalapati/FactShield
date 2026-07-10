import sys
import os
sys.path.insert(0, os.path.abspath('backend'))
from alembic.config import Config
from alembic import command
alembic_cfg = Config("backend/alembic.ini")
command.upgrade(alembic_cfg, "head")
