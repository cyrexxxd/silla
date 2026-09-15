import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

CANVAS_API_TOKEN = os.environ["CANVAS_API_TOKEN"]
CANVAS_BASE_URL = os.environ["CANVAS_BASE_URL"]

# The published Artifact dashboard's URL — set after Milestone 7 (see README).
# Empty until you've published your own dashboard.
DASHBOARD_URL = os.environ.get("DASHBOARD_URL", "")

STATE_DB_PATH = PROJECT_ROOT / "state" / "canvas.sqlite3"
ARTIFACT_PAYLOAD_PATH = PROJECT_ROOT / "artifact_payload" / "latest.json"

# Forward window for calendar/upcoming-deadlines sync, in days.
SYNC_WINDOW_DAYS = int(os.environ.get("SYNC_WINDOW_DAYS", "60"))

# Root folder for existing, manually-managed course material.
# Each course's downloaded files land in <this>/<course folder>/_synced/...
COURSE_FILES_ROOT = Path(
    os.environ.get(
        "COURSE_FILES_ROOT",
        str(Path.home() / "Documents" / "canvas files"),
    )
)

# Canvas course_id -> local folder name, for courses whose Canvas name
# doesn't match the existing manually-created folder name.
# New courses not listed here get a folder auto-created from their Canvas name.
COURSE_FOLDER_OVERRIDES: dict[int, str] = {
    # Fill in after Milestone 1 confirms real course IDs, e.g.:
    # 12345: "A & P",
    # 12346: "ICT",
    # 12347: "Linear Algebra",
    # 12348: "Mat.Analysis",
    # 12349: "english B2",
}
