"""QR code generation utility."""
import io
from typing import Optional

import qrcode
from qrcode.image.pil import PilImage


def generate_qr_code(
    url: str,
    box_size: int = 10,
    border: int = 4,
    fill_color: str = "black",
    back_color: str = "white",
) -> bytes:
    """
    Generate QR code image for a URL.

    Args:
        url: URL to encode in QR code
        box_size: Size of each box in pixels
        border: Border size in boxes
        fill_color: QR code color
        back_color: Background color

    Returns:
        PNG image bytes
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=box_size,
        border=border,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img: PilImage = qr.make_image(fill_color=fill_color, back_color=back_color)

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    return buffer.getvalue()


def generate_survey_qr(base_url: str, share_id: str) -> bytes:
    """
    Generate QR code for a survey's public URL.

    Args:
        base_url: Application base URL
        share_id: Survey's unique share ID

    Returns:
        PNG image bytes
    """
    survey_url = f"{base_url}/survey/{share_id}"
    return generate_qr_code(survey_url)
