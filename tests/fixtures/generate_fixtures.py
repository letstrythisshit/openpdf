"""Generate test fixture PDFs using reportlab directly (not through openpdf).

Run once to create all fixture files:
    python tests/fixtures/generate_fixtures.py
"""
from __future__ import annotations

import sys
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent


def generate_sample():
    """Multi-page PDF with text, a simple shape, and metadata."""
    from reportlab.pdfgen.canvas import Canvas
    from reportlab.lib.pagesizes import LETTER

    path = FIXTURES_DIR / "sample.pdf"
    c = Canvas(str(path), pagesize=LETTER)
    c.setTitle("Sample PDF")
    c.setAuthor("OpenPDF Tests")
    c.setSubject("Test fixture")

    # Page 1
    c.setFont("Helvetica", 24)
    c.drawString(72, 720, "OpenPDF Sample Document")
    c.setFont("Helvetica", 12)
    c.drawString(72, 690, "This is page 1 of the sample fixture.")
    c.drawString(72, 670, "It contains text and a rectangle.")
    c.setStrokeColorRGB(0, 0, 1)
    c.setFillColorRGB(0.9, 0.9, 1)
    c.rect(72, 580, 200, 60, stroke=1, fill=1)
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica", 10)
    c.drawString(82, 605, "A filled blue rectangle")

    # Links section
    c.setFont("Helvetica", 12)
    c.drawString(72, 540, "Visit https://example.com for more info.")

    c.showPage()

    # Page 2
    c.setFont("Helvetica-Bold", 18)
    c.drawString(72, 720, "Page 2: More Text")
    c.setFont("Times-Roman", 12)
    for i, line in enumerate([
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
        "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.",
        "Ut enim ad minim veniam, quis nostrud exercitation.",
        "Duis aute irure dolor in reprehenderit in voluptate velit esse.",
    ]):
        c.drawString(72, 690 - i * 20, line)

    c.showPage()

    # Page 3
    c.setFont("Courier", 12)
    c.drawString(72, 720, "Page 3: Monospace text and numbers")
    c.drawString(72, 700, "The quick brown fox jumps over the lazy dog.")
    c.drawString(72, 680, "0123456789 !@#$%^&*()")

    c.save()
    print(f"Created: {path}")


def generate_annotated():
    """PDF with text suitable for annotation testing."""
    from reportlab.pdfgen.canvas import Canvas
    from reportlab.lib.pagesizes import LETTER

    path = FIXTURES_DIR / "annotated.pdf"
    c = Canvas(str(path), pagesize=LETTER)
    c.setTitle("Annotated Test PDF")
    c.setFont("Helvetica", 14)
    c.drawString(72, 720, "Annotation Test Document")
    c.setFont("Helvetica", 11)
    c.drawString(72, 680, "This text can be highlighted.")
    c.drawString(72, 660, "This line can be underlined.")
    c.drawString(72, 640, "This text can be struck through.")
    c.drawString(72, 600, "REDACTABLE: sensitive information here.")
    c.save()
    print(f"Created: {path}")


def generate_form():
    """PDF with AcroForm fields."""
    import pikepdf

    path = FIXTURES_DIR / "form.pdf"
    pdf = pikepdf.Pdf.new()

    page_obj = pikepdf.Dictionary(
        Type=pikepdf.Name("/Page"),
        MediaBox=pikepdf.Array([0, 0, 612, 792]),
        Resources=pikepdf.Dictionary(),
    )
    # Content stream with text
    content = b"BT /Helvetica 12 Tf 72 720 Td (Form Test Document) Tj ET"
    stream = pdf.make_stream(content)
    page_obj["/Contents"] = pdf.make_indirect(stream)
    pdf.pages.append(pikepdf.Page(page_obj))
    page = pdf.pages[0]

    # AcroForm
    name_field = pikepdf.Dictionary(
        Type=pikepdf.Name("/Annot"),
        Subtype=pikepdf.Name("/Widget"),
        FT=pikepdf.Name("/Tx"),
        T=pikepdf.String("name"),
        V=pikepdf.String(""),
        Rect=pikepdf.Array([72, 680, 300, 700]),
        P=page.obj,
    )
    cb_field = pikepdf.Dictionary(
        Type=pikepdf.Name("/Annot"),
        Subtype=pikepdf.Name("/Widget"),
        FT=pikepdf.Name("/Btn"),
        T=pikepdf.String("agree"),
        V=pikepdf.Name("/Off"),
        AS=pikepdf.Name("/Off"),
        Rect=pikepdf.Array([72, 650, 90, 668]),
        P=page.obj,
    )

    name_ref = pdf.make_indirect(name_field)
    cb_ref = pdf.make_indirect(cb_field)
    page.obj["/Annots"] = pikepdf.Array([name_ref, cb_ref])

    acroform = pikepdf.Dictionary(
        Fields=pikepdf.Array([name_ref, cb_ref]),
    )
    pdf.Root["/AcroForm"] = pdf.make_indirect(acroform)

    pdf.save(str(path))
    print(f"Created: {path}")


def generate_toc():
    """PDF with multi-level bookmarks."""
    from reportlab.pdfgen.canvas import Canvas
    from reportlab.lib.pagesizes import LETTER
    import pikepdf

    # First create pages with reportlab
    from io import BytesIO
    buf = BytesIO()
    c = Canvas(buf, pagesize=LETTER)
    for title in ["Chapter 1", "Section 1.1", "Section 1.2", "Chapter 2"]:
        c.setFont("Helvetica-Bold", 18)
        c.drawString(72, 720, title)
        c.setFont("Helvetica", 12)
        c.drawString(72, 690, f"Content of {title}")
        c.showPage()
    c.save()

    buf.seek(0)
    pdf = pikepdf.open(buf)

    # Add outline
    with pdf.open_outline() as outline:
        from pikepdf import OutlineItem
        ch1 = OutlineItem("Chapter 1", 0)
        ch1.children.append(OutlineItem("Section 1.1", 1))
        ch1.children.append(OutlineItem("Section 1.2", 2))
        ch2 = OutlineItem("Chapter 2", 3)
        outline.root.extend([ch1, ch2])

    path = FIXTURES_DIR / "toc.pdf"
    pdf.save(str(path))
    print(f"Created: {path}")


def generate_encrypted():
    """AES-256 encrypted PDF."""
    import pikepdf

    path = FIXTURES_DIR / "encrypted.pdf"
    # Create a simple PDF first
    pdf = pikepdf.Pdf.new()
    page_dict = pikepdf.Dictionary(
        Type=pikepdf.Name("/Page"),
        MediaBox=pikepdf.Array([0, 0, 612, 792]),
        Resources=pikepdf.Dictionary(),
        Contents=pdf.make_indirect(pdf.make_stream(
            b"BT /Helvetica 12 Tf 72 720 Td (Encrypted Document) Tj ET"
        )),
    )
    pdf.pages.append(pikepdf.Page(page_dict))
    enc = pikepdf.Encryption(user="test", owner="owner", R=6)
    pdf.save(str(path), encryption=enc)
    print(f"Created: {path}")


def generate_rotated():
    """PDF with rotated pages."""
    import pikepdf

    path = FIXTURES_DIR / "rotated.pdf"
    pdf = pikepdf.Pdf.new()
    for rotation in [0, 90, 180]:
        page = pikepdf.Dictionary(
            Type=pikepdf.Name("/Page"),
            MediaBox=pikepdf.Array([0, 0, 612, 792]),
            Rotate=rotation,
            Resources=pikepdf.Dictionary(),
            Contents=pdf.make_indirect(pdf.make_stream(
                f"BT /Helvetica 12 Tf 72 720 Td ({rotation} degrees) Tj ET".encode()
            )),
        )
        pdf.pages.append(pikepdf.Page(page))
    pdf.save(str(path))
    print(f"Created: {path}")


def generate_embedded():
    """PDF with an embedded file attachment."""
    import pikepdf

    path = FIXTURES_DIR / "embedded.pdf"
    pdf = pikepdf.Pdf.new()
    page = pikepdf.Dictionary(
        Type=pikepdf.Name("/Page"),
        MediaBox=pikepdf.Array([0, 0, 612, 792]),
        Resources=pikepdf.Dictionary(),
        Contents=pdf.make_indirect(pdf.make_stream(
            b"BT /Helvetica 12 Tf 72 720 Td (Document with embedded file) Tj ET"
        )),
    )
    pdf.pages.append(pikepdf.Page(page))

    # Add embedded file
    data = b"Hello from the embedded file!"
    stream = pdf.make_stream(data)
    stream["/Type"] = pikepdf.Name("/EmbeddedFile")
    ef_dict = pikepdf.Dictionary(F=pdf.make_indirect(stream))
    spec = pikepdf.Dictionary(
        Type=pikepdf.Name("/Filespec"),
        F="hello.txt",
        EF=ef_dict,
        Desc="A test embedded file",
    )
    spec_ref = pdf.make_indirect(spec)

    pdf.Root["/Names"] = pikepdf.Dictionary(
        EmbeddedFiles=pikepdf.Dictionary(
            Names=pikepdf.Array([pikepdf.String("hello.txt"), spec_ref])
        )
    )

    pdf.save(str(path))
    print(f"Created: {path}")


def main():
    FIXTURES_DIR.mkdir(exist_ok=True)
    generate_sample()
    generate_annotated()
    generate_form()
    generate_toc()
    generate_encrypted()
    generate_rotated()
    generate_embedded()
    print("\nAll fixtures generated successfully.")


if __name__ == "__main__":
    main()
