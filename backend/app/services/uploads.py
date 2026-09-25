"""Resume upload checks. The file's type comes from its first bytes, never from its name or the
Content-Type the browser sent, so an `.exe` renamed to `.pdf` is rejected."""

import os
import re
import zipfile
from dataclasses import dataclass
from typing import BinaryIO

MAX_BYTES = 5 * 1024 * 1024

PDF_MAGIC = b"%PDF-"
OLE2_MAGIC = bytes.fromhex("D0CF11E0A1B11AE1")  # legacy .doc (and other old Office files)
ZIP_MAGIC = b"PK\x03\x04"  # .docx is a zip; checked further below

CONTENT_TYPES = {
    "pdf": "application/pdf",
    "doc": "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")


class UploadRejected(Exception):
    """The resume isn't acceptable. The message is safe to show the prospect."""


@dataclass(frozen=True)
class ResumeInfo:
    ext: str
    content_type: str
    size_bytes: int


def inspect_resume(fileobj: BinaryIO) -> ResumeInfo:
    """Check size and type. Leaves the file positioned at the start, ready to upload."""
    fileobj.seek(0, os.SEEK_END)
    size = fileobj.tell()
    fileobj.seek(0)

    if size == 0:
        raise UploadRejected("The file is empty.")
    if size > MAX_BYTES:
        raise UploadRejected("The file is larger than 5 MB.")

    ext = _detect_type(fileobj)
    fileobj.seek(0)
    if ext is None:
        raise UploadRejected("Upload a PDF, DOC or DOCX file.")

    return ResumeInfo(ext=ext, content_type=CONTENT_TYPES[ext], size_bytes=size)


def _detect_type(fileobj: BinaryIO) -> str | None:
    head = fileobj.read(8)
    if head.startswith(PDF_MAGIC):
        return "pdf"
    if head.startswith(OLE2_MAGIC):
        return "doc"
    if head.startswith(ZIP_MAGIC):
        # Any zip starts this way; a Word document has this entry inside.
        fileobj.seek(0)
        try:
            with zipfile.ZipFile(fileobj) as archive:
                if "word/document.xml" in archive.namelist():
                    return "docx"
        except zipfile.BadZipFile:
            return None
    return None


def safe_filename(name: str | None, ext: str) -> str:
    """The name we show attorneys. Only the last path segment survives, so a name like
    `../../etc/passwd.pdf` becomes `passwd.pdf`. Never used as a storage path either way."""
    base = re.split(r"[\\/]", name or "")[-1]
    base = _CONTROL_CHARS.sub("", base).strip()[:255]
    return base or f"resume.{ext}"
