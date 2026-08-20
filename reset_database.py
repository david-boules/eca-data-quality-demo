
from pathlib import Path

DB_PATH = Path(__file__).parent / "eca_demo.db"


def reset_database():

    if DB_PATH.exists():
        DB_PATH.unlink()
        print(f"Database deleted: {DB_PATH}")
    else:
        print("Database does not currently exist. Nothing to delete.")


if __name__ == "__main__":
    reset_database()
