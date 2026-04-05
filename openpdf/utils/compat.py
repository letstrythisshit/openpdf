"""PyMuPDF compatibility shims — camelCase method aliases.

This module is imported as a side effect from openpdf/__init__.py.
It assigns camelCase aliases directly on the class objects.
"""
from __future__ import annotations


def _install_compat_aliases() -> None:
    """Assign all fitz camelCase aliases onto Page, Document, and Pixmap classes."""
    from openpdf.page import Page
    from openpdf.document import Document
    from openpdf.image.rendering import Pixmap

    # ---- Page aliases ------------------------------------------------------
    Page.getText = Page.get_text
    Page.getTextPage = Page.get_textpage
    Page.searchFor = Page.search_for
    Page.getPixmap = Page.get_pixmap
    Page.getImageList = Page.get_images
    Page.getSVGimage = Page.get_svg_image
    Page.insertText = Page.insert_text
    Page.insertTextbox = Page.insert_textbox
    Page.insertImage = Page.insert_image
    Page.drawRect = Page.draw_rect
    Page.drawLine = Page.draw_line
    Page.drawCircle = Page.draw_circle
    Page.drawOval = Page.draw_oval
    Page.drawQuad = Page.draw_quad
    Page.drawPolyline = Page.draw_polyline
    Page.drawPolygon = Page.draw_polygon
    Page.drawBezier = Page.draw_bezier
    Page.drawCurve = Page.draw_curve
    Page.drawSquiggle = Page.draw_squiggle
    Page.drawZigzag = Page.draw_zigzag
    Page.drawSector = Page.draw_sector
    Page.newShape = Page.new_shape
    Page.getDrawings = Page.get_drawings
    Page.getFonts = Page.get_fonts
    Page.wrapContents = Page.wrap_contents
    Page.cleanContents = Page.clean_contents
    Page.setCropBox = Page.set_cropbox
    Page.setMediaBox = Page.set_mediabox
    Page.setRotation = Page.set_rotation
    Page.addHighlightAnnot = Page.add_highlight_annot
    Page.addUnderlineAnnot = Page.add_underline_annot
    Page.addStrikeoutAnnot = Page.add_strikeout_annot
    Page.addSquigglyAnnot = Page.add_squiggly_annot
    Page.addFreetextAnnot = Page.add_freetext_annot
    Page.addTextAnnot = Page.add_text_annot
    Page.addLineAnnot = Page.add_line_annot
    Page.addRectAnnot = Page.add_rect_annot
    Page.addCircleAnnot = Page.add_circle_annot
    Page.addPolygonAnnot = Page.add_polygon_annot
    Page.addPolylineAnnot = Page.add_polyline_annot
    Page.addInkAnnot = Page.add_ink_annot
    Page.addStampAnnot = Page.add_stamp_annot
    Page.addFileAnnot = Page.add_file_annot
    Page.addCaretAnnot = Page.add_caret_annot
    Page.addRedactAnnot = Page.add_redact_annot
    Page.applyRedactions = Page.apply_redactions
    Page.deleteAnnot = Page.delete_annot
    Page.insertLink = Page.insert_link
    Page.deleteLink = Page.delete_link
    Page.getLinks = Page.get_links

    # ---- Document aliases --------------------------------------------------
    Document.loadPage = Document.load_page
    Document.newPage = Document.new_page
    Document.insertPage = Document.insert_page
    Document.deletePage = Document.delete_page
    Document.deletePages = Document.delete_pages
    Document.copyPage = Document.copy_page
    Document.movePage = Document.move_page
    Document.insertPDF = Document.insert_pdf
    Document.insertFile = Document.insert_file
    Document.setMetadata = Document.set_metadata
    Document.getToC = Document.get_toc
    Document.setToC = Document.set_toc
    Document.embeddedFileCount = Document.embfile_count
    Document.embeddedFileNames = Document.embfile_names
    Document.embeddedFileGet = Document.embfile_get
    Document.embeddedFileAdd = Document.embfile_add
    Document.embeddedFileDel = Document.embfile_del
    Document.convertToPDF = Document.convert_to_pdf
    Document.write = Document.write  # already same name

    # ---- Pixmap aliases ----------------------------------------------------
    Pixmap.getPNGData = lambda self: self.tobytes("png")
    Pixmap.writePNG = lambda self, f: self.save(f, "png")
    Pixmap.getImageData = Pixmap.tobytes


# Install immediately on import
_install_compat_aliases()
