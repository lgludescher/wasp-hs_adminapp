import io
from typing import Any, List, Dict
from openpyxl import Workbook


def generate_excel_response(
    data: List[Dict[str, Any]],
    headers: List[str],
    sheet_title: str = "Sheet1"
) -> io.BytesIO:
    """
    Generates an in-memory Excel file from a list of dictionaries.

    Args:
        data: A list of dictionaries, where each dictionary represents a row.
        headers: A list of strings for the header row. The keys in the data
                 dictionaries should match these headers.
        sheet_title: The title of the worksheet.

    Returns:
        An in-memory BytesIO buffer containing the Excel file.
    """
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = sheet_title

    # Write the header row
    sheet.append(headers)

    # Write data rows
    for item in data:
        row = [item.get(header, "") for header in headers]
        sheet.append(row)

    # Save the workbook to an in-memory buffer
    buffer = io.BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    return buffer
