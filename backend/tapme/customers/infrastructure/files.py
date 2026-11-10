import csv
import re
from io import BytesIO, StringIO
from zipfile import BadZipFile, ZipFile

from openpyxl import Workbook, load_workbook
from openpyxl.cell import WriteOnlyCell

from tapme.customers.infrastructure.vcards import read_vcards
from tapme.shared.domain import InvalidInput

HEADERS = {
    "name": "name",
    "имя": "name",
    "имя клиента": "name",
    "phone": "phone",
    "телефон": "phone",
    "notes": "notes",
    "заметка": "notes",
    "additional_phones": "additional_phones",
    "дополнительные телефоны": "additional_phones",
}
MAX_XLSX_ROWS = 5000  # Includes the header and blank rows.
MAX_XLSX_COLUMNS = 64


def xlsx_rows(sheet):
    message = f"Лист Excel должен содержать до {MAX_XLSX_ROWS} строк и {MAX_XLSX_COLUMNS} столбцов."
    if (sheet.max_row or 0) > MAX_XLSX_ROWS or (sheet.max_column or 0) > MAX_XLSX_COLUMNS:
        raise InvalidInput(message)
    # XLSX dimensions are supplied by the file and may be absent or inaccurate.
    # Limit the iterator independently so row gaps cannot expand the work.
    sheet.reset_dimensions()
    for number, row in enumerate(
        sheet.iter_rows(min_row=1, min_col=1, max_row=MAX_XLSX_ROWS + 1, values_only=True),
        1,
    ):
        if number > MAX_XLSX_ROWS or len(row) > MAX_XLSX_COLUMNS:
            raise InvalidInput(message)
        yield row


def read_customers(upload):
    if upload.size > 2 * 1024 * 1024:
        raise InvalidInput("Файл должен занимать не более 2 МБ.")
    data = upload.read()
    if upload.name.lower().endswith((".vcf", ".vcard")):
        return read_vcards(data)
    workbook = None
    try:
        if upload.name.lower().endswith(".csv"):
            content = data.decode("utf-8-sig")
            try:
                delimiter = csv.Sniffer().sniff(content[:4096], delimiters=",;\t").delimiter
            except csv.Error:
                delimiter = ","
            iterator = iter(csv.reader(StringIO(content), delimiter=delimiter))
        elif upload.name.lower().endswith(".xlsx"):
            with ZipFile(BytesIO(data)) as archive:
                if (
                    sum(entry.file_size for entry in archive.infolist()) > 20 * 1024 * 1024
                    or len(archive.infolist()) > 1000
                ):
                    raise InvalidInput("Слишком большой распакованный Excel-файл.")
            workbook = load_workbook(
                BytesIO(data), read_only=True, data_only=True, keep_links=False
            )
            if not workbook.worksheets:
                raise InvalidInput("В Excel-файле нет листов с контактами.")
            iterator = xlsx_rows(workbook.worksheets[0])
        else:
            raise InvalidInput("Поддерживаются CSV в UTF-8, XLSX и VCF (vCard).")
        header = [HEADERS.get(str(cell or "").strip().lower(), "") for cell in next(iterator)]
        if "name" not in header or "phone" not in header:
            raise InvalidInput(
                "Нужны столбцы name (имя) и phone (телефон), notes (заметка) необязателен."
            )
        rows = []
        for row in iterator:
            if not any(value is not None and str(value).strip() for value in row):
                continue
            rows.append(
                {
                    key: str(row[i] if i < len(row) and row[i] is not None else "").strip()
                    for i, key in enumerate(header)
                    if key
                }
            )
            extra = rows[-1].get("additional_phones", "")
            rows[-1]["additional_phones"] = [
                number.strip() for number in re.split(r"[;\n]", extra) if number.strip()
            ]
            if len(rows) > 1000:
                raise InvalidInput("Не более 1000 строк в одном импорте.")
        return rows
    except (UnicodeError, csv.Error, StopIteration, BadZipFile, ValueError, KeyError, OSError):
        raise InvalidInput("Не удалось прочитать таблицу. Проверьте формат и заголовки.") from None
    finally:
        if workbook:
            workbook.close()


def export_customers(rows, kind):
    fields = ("name", "phone", "notes", "additional_phones")
    if kind == "xlsx":
        book = Workbook(write_only=True)
        sheet = book.create_sheet("Клиенты")
        sheet.append(list(fields))
        for row in rows:
            cells = []
            for key in fields:
                cell = WriteOnlyCell(sheet, value=row.get(key, ""))
                cell.data_type = "s"
                cells.append(cell)
            sheet.append(cells)
        stream = BytesIO()
        book.save(stream)
        return (
            stream.getvalue(),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    stream = StringIO()
    writer = csv.writer(stream)
    writer.writerow(fields)
    for row in rows:
        writer.writerow(
            [
                "'" + row.get(key, "")
                if row.get(key, "").lstrip().startswith(("=", "+", "-", "@"))
                else row.get(key, "")
                for key in fields
            ]
        )
    return stream.getvalue().encode("utf-8-sig"), "text/csv; charset=utf-8"
