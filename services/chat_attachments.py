from io import BytesIO
from pathlib import PurePath
from zipfile import BadZipFile

from docx import Document
from docx.opc.exceptions import PackageNotFoundError
from pypdf import PdfReader
from pypdf.errors import PdfReadError

MAX_ATTACHMENT_BYTES = 8 * 1024 * 1024
MAX_ATTACHMENT_TEXT_CHARS = 12_000
SUPPORTED_EXTENSIONS = {".csv", ".docx", ".md", ".pdf", ".txt"}


class ChatAttachmentError(ValueError):
    pass


def extract_attachment_text(filename: str, content: bytes) -> str:
    extension = PurePath(filename).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise ChatAttachmentError(
            "Adjunta un archivo PDF, TXT, Markdown, CSV o DOCX."
        )
    if len(content) > MAX_ATTACHMENT_BYTES:
        raise ChatAttachmentError("El archivo no puede superar los 8 MB.")

    try:
        if extension == ".pdf":
            text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(content)).pages)
        elif extension == ".docx":
            document = Document(BytesIO(content))
            text = "\n".join(paragraph.text for paragraph in document.paragraphs)
        else:
            text = content.decode("utf-8-sig")
    except (BadZipFile, PackageNotFoundError, PdfReadError, UnicodeDecodeError) as error:
        raise ChatAttachmentError(
            "No se pudo leer el archivo. Verifica que no esté dañado y que use texto UTF-8."
        ) from error

    text = text.strip()
    if not text:
        raise ChatAttachmentError("No se encontró texto extraíble en el archivo.")
    if len(text) > MAX_ATTACHMENT_TEXT_CHARS:
        raise ChatAttachmentError(
            "El archivo contiene demasiado texto. El límite extraído es de 12.000 caracteres."
        )
    return text


def format_attachment_message(message: str, filename: str, text: str) -> str:
    safe_filename = filename.replace("\\", "/").rsplit("/", 1)[-1]
    safe_filename = " ".join(safe_filename.replace("---", "—").split())[:255]
    return f"{message}\n\n--- Archivo adjunto: {safe_filename} ---\n{text}"
