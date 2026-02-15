from __future__ import annotations

import os
import subprocess
import tempfile
from shutil import which


class DocConverter:
    @staticmethod
    def to_docx(source_path: str) -> str:
        if which("soffice") is None and which("libreoffice") is None:
            raise RuntimeError("LibreOffice is required to convert .doc files")

        output_dir = tempfile.mkdtemp()
        command = [
            "soffice",
            "--headless",
            "--convert-to",
            "docx",
            "--outdir",
            output_dir,
            source_path,
        ]
        try:
            subprocess.run(
                command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
        except subprocess.CalledProcessError as exc:
            raise RuntimeError("Failed to convert .doc to .docx") from exc

        base_name = os.path.splitext(os.path.basename(source_path))[0]
        docx_path = os.path.join(output_dir, f"{base_name}.docx")
        if not os.path.exists(docx_path):
            raise RuntimeError("Converted .docx file not found")
        return docx_path
