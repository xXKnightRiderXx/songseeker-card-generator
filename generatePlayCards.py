import argparse
import hashlib
import io
import os
import pandas as pd
import qrcode
import textwrap
import requests
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from qrcode.image.styledpil import StyledPilImage


def generate_qr_code(url: str, file_path: str, icon_path: str | None, icon_image_cache: dict[str, io.BytesIO] = {}):
    qr_code = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_Q,
        box_size=10,
        border=4,
    )
    qr_code.add_data(url)
    qr_code.make(fit=True)
    if icon_path is None:
        img = qr_code.make_image(fill_color="black", back_color="white")
    else:
        if icon_path.startswith("http"):
            if icon_path not in icon_image_cache:
                response = requests.get(icon_path)
                icon_image_cache[icon_path] = io.BytesIO(response.content)
            icon_image = icon_image_cache[icon_path]
            img = qr_code.make_image(image_factory=StyledPilImage, embeded_image_path=icon_image)
        else:
            img = qr_code.make_image(image_factory=StyledPilImage, embeded_image_path=icon_path)
    img.save(file_path)


def add_qr_code_with_border(
    page_canvas: canvas.Canvas, url: str, position: tuple[float, float], box_size: float, icon_path: str | None
):
    hash_object = hashlib.sha256(url.encode())
    hex_dig = hash_object.hexdigest()
    qr_code_path = f"qr_{hex_dig}.png"  # Unique path for each QR code
    generate_qr_code(url, qr_code_path, icon_path)
    x, y = position
    page_canvas.drawImage(qr_code_path, x, y, width=box_size, height=box_size)
    # c.rect(x, y, box_size, box_size)
    os.remove(qr_code_path)


def add_text_box(
    page_canvas: canvas.Canvas,
    info: pd.Series,
    position: tuple[float, float],
    box_size: float,
    font_artist: str = "Helvetica-Bold",
    font_size_artist: int = 14,
    font_title: str = "Helvetica",
    font_size_title: int = 14,
    font_year: str = "Helvetica-Bold",
    font_size_year: int = 50,
):
    x, y = position
    text_margin = 5
    text_indent = 8

    default_font_color = "0,0,0"  # Default color is black

    # Check if 'backcol' is in info and set the fill color
    if "backcol" in info and not pd.isna(info["backcol"]):
        r, g, b = tuple(float(x) for x in info["backcol"].split(","))
        page_canvas.setFillColorRGB(r, g, b)
        page_canvas.rect(x, y, box_size, box_size, fill=1)
    else:
        page_canvas.rect(x, y, box_size, box_size)

    r, g, b = tuple(float(x) for x in default_font_color.split(","))
    page_canvas.setFillColorRGB(r, g, b)

    # Calculate the centered position for each line of text
    if not pd.isna(info["Artist"]):
        artist_text = f"{info['Artist']}"
        artist_x = x + (box_size - page_canvas.stringWidth(artist_text, font_artist, font_size_artist)) / 2
        artist_lines = textwrap.wrap(
            artist_text,
            width=int(
                len(artist_text)
                / page_canvas.stringWidth(artist_text, font_artist, font_size_artist)
                * (box_size - text_indent * 2)
            ),
        )
        artist_y = y + box_size - (text_indent + font_size_artist)
        for line in artist_lines:
            artist_x = x + (box_size - page_canvas.stringWidth(line, font_artist, font_size_artist)) / 2
            page_canvas.setFont(font_artist, font_size_artist)
            page_canvas.drawString(artist_x, artist_y, line)
            artist_y -= text_margin + font_size_artist

    if not pd.isna(info["Title"]):
        title_text = f"{info['Title']}"
        title_x = x + (box_size - page_canvas.stringWidth(title_text, font_title, font_size_title)) / 2
        title_lines = textwrap.wrap(
            title_text,
            width=int(
                len(title_text)
                / page_canvas.stringWidth(title_text, font_title, font_size_title)
                * (box_size - text_indent * 2)
            ),
        )
        title_y = y + (len(title_lines) - 1) * (text_margin + font_size_title) + font_size_title / 2 + text_indent
        for line in title_lines:
            title_x = x + (box_size - page_canvas.stringWidth(line, font_title, font_size_title)) / 2
            page_canvas.setFont(font_title, font_size_title)
            page_canvas.drawString(title_x, title_y, line)
            title_y -= text_margin + font_size_title

    if not pd.isna(info["Year"]):
        year_text = f"{info['Year']}"
        year_x = x + (box_size - page_canvas.stringWidth(year_text, font_year, font_size_year)) / 2
        year_y = y + box_size / 2 - (font_size_year / 2) / 2

    page_canvas.setFont(font_year, font_size_year)
    page_canvas.drawString(year_x, year_y, year_text)


def main(csv_file_path: str, output_pdf_path: str, icon_path: str | None = None):
    data = pd.read_csv(csv_file_path)
    data = data.map(lambda x: x.strip() if isinstance(x, str) else x)  # Remove leading and trailing whitespaces

    page_canvas = canvas.Canvas(output_pdf_path, pagesize=A4)
    page_width, page_height = A4
    box_size = 6.5 * cm
    boxes_per_row = int(page_width // box_size)
    boxes_per_column = int(page_height // box_size)
    boxes_per_page = boxes_per_row * boxes_per_column
    vertical_page_indent = 0.8 * cm
    horizontal_page_indent = (page_width - (box_size * boxes_per_row)) / 2

    for i in range(0, len(data), boxes_per_page):
        # Generate QR codes
        for index in range(i, min(i + boxes_per_page, len(data))):
            row = data.iloc[index]
            position_index = index % (boxes_per_row * boxes_per_column)
            column_index = position_index % boxes_per_row
            row_index = position_index // boxes_per_row
            x = horizontal_page_indent + (column_index * box_size)
            y = page_height - vertical_page_indent - (row_index + 1) * box_size
            add_qr_code_with_border(page_canvas, row["URL"], (x, y), box_size, icon_path)

        page_canvas.showPage()

        # Add text information
        for index in range(i, min(i + boxes_per_page, len(data))):
            row = data.iloc[index]
            position_index = index % boxes_per_page
            column_index = (boxes_per_row - 1) - position_index % boxes_per_row
            row_index = position_index // boxes_per_row
            x = horizontal_page_indent + (column_index * box_size)
            y = page_height - vertical_page_indent - (row_index + 1) * box_size
            add_text_box(page_canvas, row, (x, y), box_size)

        page_canvas.showPage()

    page_canvas.save()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_file", help="Path to the CSV file")
    parser.add_argument("output_pdf", help="Path to the output PDF file")
    parser.add_argument(
        "--icon",
        help="Path to icon to embed to QR Code, should not exceed 300x300px and using transparent background",
        required=False,
    )
    args = parser.parse_args()
    main(args.csv_file, args.output_pdf, args.icon)
