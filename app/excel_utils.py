import io
from typing import Any, List, Dict, Optional
from openpyxl import Workbook


def generate_excel_response(
    data: List[Dict[str, Any]],
    headers: List[str],
    sheet_title: str = "Sheet1",
    filter_info: Optional[List[str]] = None
) -> io.BytesIO:
    """
    Generates an in-memory Excel file from a list of dictionaries.

    Args:
        data: A list of dictionaries, where each dictionary represents a row.
        headers: A list of strings for the header row. The keys in the data
                 dictionaries should match these headers.
        sheet_title: The title of the worksheet.
        filter_info: An optional list of strings to print as header
                     lines before the main data, documenting the filters used.

    Returns:
        An in-memory BytesIO buffer containing the Excel file.
    """
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = sheet_title

    # If filter information is provided, write it to the top rows
    if filter_info:
        for info_line in filter_info:
            sheet.append([info_line])  # Append as a single-cell row
        sheet.append([])  # Add a blank row for spacing

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
