from io import BytesIO

import pytest
from docx import Document

from services.chat_attachments import (
    ChatAttachmentError,
    extract_attachment_text,
    format_attachment_message,
)


def test_extracts_utf8_text_attachments():
    assert extract_attachment_text("manual.TXT", b"\xef\xbb\xbfMotor y frenos") == (
        "Motor y frenos"
    )


def test_extracts_docx_paragraphs():
    document = Document()
    document.add_paragraph("Motor y frenos")
    buffer = BytesIO()
    document.save(buffer)

    assert extract_attachment_text("manual.docx", buffer.getvalue()) == (
        "Motor y frenos"
    )


def test_rejects_unsupported_and_oversized_attachments():
    with pytest.raises(ChatAttachmentError, match="PDF, TXT"):
        extract_attachment_text("foto.png", b"contenido")

    with pytest.raises(ChatAttachmentError, match="8 MB"):
        extract_attachment_text("manual.txt", b"x" * (8 * 1024 * 1024 + 1))


def test_rejects_non_utf8_and_empty_text_files():
    with pytest.raises(ChatAttachmentError, match="No se pudo leer"):
        extract_attachment_text("manual.txt", b"\xff")

    with pytest.raises(ChatAttachmentError, match="No se encontró texto"):
        extract_attachment_text("manual.txt", b" \r\n ")


def test_formats_attachment_context_without_path_information():
    assert format_attachment_message(
        "Explica esto", r"C:\privado\manual---motor.pdf", "Contenido"
    ) == "Explica esto\n\n--- Archivo adjunto: manual—motor.pdf ---\nContenido"
