"""Canvas Files/Folders diff + download into <course>/_synced/, mirroring Canvas's structure.

Never touches anything outside a course's own _synced/ subfolder.
"""
import re
import time

import requests

from . import config, state_store

_SANITIZE_RE = re.compile(r'[\/:*?"<>|]')


def sanitize_name(name: str) -> str:
    return _SANITIZE_RE.sub("_", name).strip()


def local_folder_for_course(course_id: int, canvas_name: str) -> str:
    return config.COURSE_FOLDER_OVERRIDES.get(course_id, sanitize_name(canvas_name))


def synced_root_for_course(course_id: int, canvas_name: str):
    folder_name = local_folder_for_course(course_id, canvas_name)
    root = config.COURSE_FILES_ROOT / folder_name / "_synced"
    root.mkdir(parents=True, exist_ok=True)
    return root, folder_name


def sync_course_files(canvas_client_with_retry, conn, course, synced_root, errors: list | None = None) -> int:
    """Download new/changed files for one course. Returns count of files downloaded.

    A single flaky file (timeout, broken signed URL) is logged to `errors` and skipped
    rather than aborting the rest of the course's file sync.
    """
    downloaded = 0
    errors = errors if errors is not None else []

    folders = list(canvas_client_with_retry(course.get_folders))
    folder_paths = {f.id: f.full_name for f in folders}

    files = list(canvas_client_with_retry(course.get_files, per_page=100))
    for f in files:
        canvas_file_id = f.id
        filename = f.display_name
        updated_at = getattr(f, "updated_at", None)
        size_bytes = getattr(f, "size", None)
        folder_path = folder_paths.get(f.folder_id, "course files")
        # Canvas folder paths look like "course files/Week 1"; strip the redundant prefix.
        rel_folder = folder_path.split("course files", 1)[-1].strip("/")

        known = state_store.get_known_file(conn, canvas_file_id)
        needs_download = known is None or known["canvas_updated_at"] != updated_at

        dest_dir = synced_root / rel_folder if rel_folder else synced_root
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / sanitize_name(filename)

        if needs_download and getattr(f, "url", None):
            try:
                resp = requests.get(f.url, timeout=60)
                resp.raise_for_status()
                dest_path.write_bytes(resp.content)
                downloaded += 1
                time.sleep(0.05)  # be polite to signed-URL storage backend
            except requests.exceptions.RequestException as exc:
                errors.append(f"course {course.id} file {filename!r}: download failed: {exc!r}")
                continue  # don't record file metadata as synced if the download failed

        state_store.upsert_file(
            conn,
            canvas_file_id=canvas_file_id,
            course_id=course.id,
            course_name=course.name,
            filename=filename,
            canvas_updated_at=updated_at,
            size_bytes=size_bytes,
            folder_path=rel_folder,
            local_path=str(dest_path),
            canvas_url=f"{config.CANVAS_BASE_URL}/courses/{course.id}/files/{canvas_file_id}",
        )

    return downloaded
