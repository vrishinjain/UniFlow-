import reflex as rx

import asyncio
import io
import logging
import re
from pathlib import PurePosixPath
from typing import TypedDict
from xml.etree import ElementTree as ET
from zipfile import BadZipFile, ZipFile

MAX_FILES = 3
MAX_FILE_BYTES = 10 * 1024 * 1024
MIME_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}


class ValidatedFile(TypedDict):
    filename: str
    data: bytes
    size_bytes: int
    content_type: str


def _safe_filename(filename: str) -> str:
    if (
        not isinstance(filename, str)
        or not filename.strip()
        or filename != filename.strip()
        or len(filename) > 255
        or any(ord(char) < 32 or ord(char) == 127 for char in filename)
        or any(char in filename for char in ("/", "\\", ":"))
        or filename in {".", ".."}
    ):
        raise ValueError(
            "An attachment has an invalid filename. Use a plain filename without folders."
        )
    if PurePosixPath(filename).suffix.lower() not in MIME_TYPES:
        raise ValueError("Only PDF, DOCX, and PPTX attachments are allowed.")
    return filename


def _xml_part(archive: ZipFile, name: str) -> ET.Element:
    info = archive.getinfo(name)
    if info.file_size > 2 * 1024 * 1024:
        raise ValueError("An attachment has oversized document metadata.")
    with archive.open(info) as stream:
        data = stream.read(2 * 1024 * 1024 + 1)
    if (
        len(data) > 2 * 1024 * 1024
        or b"<!DOCTYPE" in data.upper()
        or b"<!ENTITY" in data.upper()
    ):
        raise ValueError(
            "An attachment contains unsupported document metadata."
        )
    return ET.fromstring(data)


def _validate_ooxml(data: bytes, extension: str):
    main, root_tag, main_type = (
        (
            "word/document.xml",
            "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}document",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml",
        )
        if extension == ".docx"
        else (
            "ppt/presentation.xml",
            "{http://schemas.openxmlformats.org/presentationml/2006/main}presentation",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml",
        )
    )
    try:
        with ZipFile(io.BytesIO(data)) as archive:
            entries = archive.infolist()
            names = [entry.filename for entry in entries]
            if len(entries) > 4096 or len(names) != len(set(names)):
                raise ValueError(
                    "An attachment has an unsupported document archive."
                )
            if not {"[Content_Types].xml", "_rels/.rels", main}.issubset(names):
                raise ValueError(
                    "An attachment is not a valid DOCX or PPTX document."
                )
            if sum(entry.file_size for entry in entries) > 100 * 1024 * 1024:
                raise ValueError(
                    "An attachment expands beyond the supported document size."
                )
            for entry in entries:
                path = PurePosixPath(entry.filename)
                if (
                    path.is_absolute()
                    or ".." in path.parts
                    or "\\" in entry.filename
                    or entry.flag_bits & 1
                ):
                    raise ValueError(
                        "An attachment contains unsafe or encrypted document entries."
                    )
                if "vbaproject" in entry.filename.lower():
                    raise ValueError(
                        "Macro-enabled documents are not supported."
                    )
            types = _xml_part(archive, "[Content_Types].xml")
            namespace = (
                "{http://schemas.openxmlformats.org/package/2006/content-types}"
            )
            if types.tag != f"{namespace}Types" or not any(
                item.attrib.get("PartName") == f"/{main}"
                and item.attrib.get("ContentType") == main_type
                for item in types.findall(f"{namespace}Override")
            ):
                raise ValueError(
                    "An attachment's document type does not match its extension."
                )
            relationships = _xml_part(archive, "_rels/.rels")
            rel_ns = (
                "{http://schemas.openxmlformats.org/package/2006/relationships}"
            )
            if relationships.tag != f"{rel_ns}Relationships" or not any(
                item.attrib.get("Type")
                == "http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"
                and item.attrib.get("Target", "").lstrip("/") == main
                and item.attrib.get("TargetMode", "Internal") == "Internal"
                for item in relationships.findall(f"{rel_ns}Relationship")
            ):
                raise ValueError(
                    "An attachment is missing its main document relationship."
                )
            if _xml_part(archive, main).tag != root_tag:
                raise ValueError(
                    "An attachment's contents do not match its document type."
                )
    except (
        BadZipFile,
        KeyError,
        ET.ParseError,
        RuntimeError,
        OSError,
        NotImplementedError,
    ) as e:
        logging.exception(f"Error: {e}")
        raise ValueError(
            "An attachment is damaged or is not a valid DOCX or PPTX document."
        ) from e


def _validate_signature(data: bytes, extension: str):
    if extension == ".pdf":
        if re.match(rb"%PDF-[12]\.[0-9](?:\r|\n|\s)", data[:16]) is None:
            raise ValueError("An attachment is not a valid PDF file.")
    else:
        _validate_ooxml(data, extension)


async def read_and_validate(files: list[rx.UploadFile]) -> list[ValidatedFile]:
    """Validate the complete selection in memory; never persist attachments."""
    if len(files) > MAX_FILES:
        raise ValueError("Choose at most 3 attachments. Nothing was saved.")
    validated: list[ValidatedFile] = []
    for file in files:
        filename = _safe_filename(file.name or "")
        extension = PurePosixPath(filename).suffix.lower()
        try:
            data = await file.read(MAX_FILE_BYTES + 1)
        except Exception as e:
            logging.exception(f"Error: {e}")
            raise ValueError(
                "An attachment could not be read. Select it again and retry."
            ) from e
        if len(data) > MAX_FILE_BYTES:
            raise ValueError(
                "Each attachment must be 10 MB or smaller. Nothing was saved."
            )
        await asyncio.to_thread(_validate_signature, data, extension)
        validated.append(
            ValidatedFile(
                filename=filename,
                data=data,
                size_bytes=len(data),
                content_type=MIME_TYPES[extension],
            )
        )
    return validated
