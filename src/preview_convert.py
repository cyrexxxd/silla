"""Convert Office documents (.pptx/.docx/.xlsx/...) to PDF via headless LibreOffice so
the local dashboard can preview them inline in the browser instead of just downloading
them. Entirely optional: if `soffice` isn't installed, conversion is silently skipped and
the dashboard falls back to a direct download link — nothing else breaks.
"""
import shutil
import subprocess

CONVERTIBLE_EXTENSIONS = {
    ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx", ".odt", ".odp", ".ods", ".rtf",
}


def soffice_available() -> bool:
    return shutil.which("soffice") is not None


def needs_conversion(filename: str) -> bool:
    dot = filename.rfind(".")
    ext = filename[dot:].lower() if dot != -1 else ""
    return ext in CONVERTIBLE_EXTENSIONS


def convert_to_pdf(src_path, out_dir) -> "str | None":
    """Convert src_path to a PDF in out_dir. Returns the PDF path, or None on failure."""
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(
            [
                "soffice", "--headless", "--norestore",
                "--convert-to", "pdf", "--outdir", str(out_dir), str(src_path),
            ],
            capture_output=True,
            timeout=120,
            check=True,
        )
    except (subprocess.SubprocessError, OSError):
        return None
    pdf_path = out_dir / (src_path.stem + ".pdf")
    return str(pdf_path) if pdf_path.exists() else None
