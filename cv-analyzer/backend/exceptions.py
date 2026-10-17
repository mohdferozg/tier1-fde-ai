"""Custom exceptions for the CV Analyzer backend.

Each exception class represents a distinct failure domain. Callers — such as
FastAPI endpoints — can catch them specifically and translate them into
appropriate HTTP responses without parsing error message strings.
"""


class PdfExtractionError(Exception):
    """Raised when a PDF cannot be parsed or contains no extractable text.

    Distinct from FileNotFoundError, which is raised when the file does not
    exist. This error means the file exists (or was provided as a stream) but
    the content cannot be turned into usable text. Common causes:

    - The file is not actually a PDF (corrupt or wrong format)
    - The PDF is encrypted and cannot be read without a password
    - The PDF is image-only (scanned) and contains no extractable text
    """