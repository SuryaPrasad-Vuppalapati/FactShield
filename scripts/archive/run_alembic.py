from alembic import command
from alembic.config import Config
import sys
import os
sys.path.insert(0, os.path.abspath('backend'))
alembic_cfg = Config("backend/alembic.ini")
command.upgrade(alembic_cfg, "head")
