from pathlib import Path
from alembic import command
from alembic.config import Config


def main():
    Path("data").mkdir(exist_ok=True)
    command.upgrade(Config("alembic.ini"), "head")
    print("Migrations appliquées — SQLite prêt")


if __name__ == "__main__":
    main()
