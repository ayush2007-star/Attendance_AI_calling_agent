from pydantic import BaseModel


class StudentImportResponse(BaseModel):
    total_rows: int
    created_rows: int
    invalid_rows: int
    duplicate_rows: int
    errors: list[str]
