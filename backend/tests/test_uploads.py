import io
import zipfile

import pytest

from app.services.uploads import MAX_BYTES, UploadRejected, inspect_resume, safe_filename

PDF = b"%PDF-1.7\n%fake but well-formed enough\n"
DOC = bytes.fromhex("D0CF11E0A1B11AE1") + b"\x00" * 64
EXE = b"MZ\x90\x00" + b"\x00" * 64


def make_zip(*names: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name in names:
            archive.writestr(name, "x")
    return buffer.getvalue()


DOCX = make_zip("[Content_Types].xml", "word/document.xml")


@pytest.mark.parametrize(
    ("data", "ext"),
    [(PDF, "pdf"), (DOC, "doc"), (DOCX, "docx")],
)
def test_accepts_pdf_doc_docx_by_content(data, ext):
    info = inspect_resume(io.BytesIO(data))

    assert info.ext == ext
    assert info.size_bytes == len(data)


@pytest.mark.parametrize(
    "data",
    [EXE, make_zip("notes.txt"), b"just some text", b"PK\x03\x04 not really a zip"],
    ids=["exe", "plain-zip", "text", "corrupt-zip"],
)
def test_rejects_anything_else(data):
    with pytest.raises(UploadRejected, match="PDF, DOC or DOCX"):
        inspect_resume(io.BytesIO(data))


def test_rejects_empty_file():
    with pytest.raises(UploadRejected, match="empty"):
        inspect_resume(io.BytesIO(b""))


def test_rejects_file_over_5_mb():
    with pytest.raises(UploadRejected, match="5 MB"):
        inspect_resume(io.BytesIO(PDF + b"0" * MAX_BYTES))


def test_leaves_file_at_start_for_upload():
    fileobj = io.BytesIO(DOCX)
    inspect_resume(fileobj)

    assert fileobj.tell() == 0


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("resume.pdf", "resume.pdf"),
        ("../../etc/passwd.pdf", "passwd.pdf"),
        ("C:\\Users\\ada\\cv.docx", "cv.docx"),
        ("bad\r\nname.pdf", "badname.pdf"),
        ("", "resume.pdf"),
        (None, "resume.pdf"),
        ("../", "resume.pdf"),
    ],
)
def test_safe_filename_keeps_only_the_last_segment(name, expected):
    assert safe_filename(name, "pdf") == expected
