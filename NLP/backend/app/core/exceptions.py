"""
Custom application exceptions with structured payload.
"""
from __future__ import annotations


class AppError(Exception):
    """Base class for all application-level errors."""

    status_code: int = 500
    code: str = "INTERNAL_ERROR"

    def __init__(self, error: str, detail: str = "", code: str | None = None):
        super().__init__(error)
        self.error = error
        self.detail = detail
        if code:
            self.code = code

    def to_dict(self) -> dict:
        return {"error": self.error, "detail": self.detail, "code": self.code}


class DatasetNotFound(AppError):
    status_code = 404
    code = "DATASET_NOT_FOUND"

    def __init__(self, dataset_id: str):
        super().__init__(
            error=f"Dataset '{dataset_id}' not found",
            detail="The requested dataset does not exist or has been deleted.",
        )


class ProcessingError(AppError):
    status_code = 422
    code = "PROCESSING_ERROR"

    def __init__(self, error: str, detail: str = ""):
        super().__init__(error=error, detail=detail)


class QueryValidationError(AppError):
    status_code = 400
    code = "QUERY_VALIDATION_ERROR"

    def __init__(self, error: str, detail: str = ""):
        super().__init__(error=error, detail=detail)


class NLPParseError(AppError):
    status_code = 422
    code = "NLP_PARSE_ERROR"

    def __init__(self, error: str, detail: str = ""):
        super().__init__(error=error, detail=detail)


class DashboardNotFound(AppError):
    status_code = 404
    code = "DASHBOARD_NOT_FOUND"

    def __init__(self, dashboard_id: str):
        super().__init__(
            error=f"Dashboard '{dashboard_id}' not found",
            detail="The requested dashboard does not exist.",
        )


class ReportNotFound(AppError):
    status_code = 404
    code = "REPORT_NOT_FOUND"

    def __init__(self, report_id: str):
        super().__init__(
            error=f"Report '{report_id}' not found",
            detail="The requested report does not exist.",
        )
