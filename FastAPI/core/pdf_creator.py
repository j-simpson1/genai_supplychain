import json
import re
import os
from typing import List, Dict, Optional, Tuple
from pathlib import Path

from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import Color
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import LETTER
from reportlab.platypus.frames import Frame
from reportlab.platypus.doctemplate import PageTemplate
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image,
    ListFlowable, ListItem
)


class PDFReportGenerator:
    """A class to generate PDF reports with support for various formatting options."""

    # Constants
    LOGO_WIDTH = 1.5 * inch
    LOGO_HEIGHT = 0.75 * inch
    IMAGE_WIDTH = 3.75 * inch
    IMAGE_HEIGHT = 2.75 * inch
    NAVY_BLUE = Color(19 / 255, 52 / 255, 92 / 255)

    def __init__(self, filename: str = "report.pdf"):
        """Initialize the PDF generator with a filename."""
        self.filename = self._ensure_pdf_extension(filename)
        self.styles = self._setup_styles()
        self.logo_path = self._get_logo_path()

    @staticmethod
    def _ensure_pdf_extension(filename: str) -> str:
        """Ensure the filename has a .pdf extension."""
        return filename if filename.endswith(".pdf") else f"{filename}.pdf"

    @staticmethod
    def _get_logo_path() -> Path:
        """Get the path to the logo file."""
        BASE_DIR = Path(__file__).resolve().parent.parent
        return BASE_DIR / "static" / "Alvarez_and_Marsal.png"

    def _setup_styles(self) -> Dict:
        """Set up and customize the document styles."""
        styles = getSampleStyleSheet()

        # Font sizes
        styles["Title"].fontSize = 20
        styles["Heading1"].fontSize = 16
        styles["Heading2"].fontSize = 14
        styles["Heading3"].fontSize = 12

        # Spacing
        styles["Heading1"].spaceBefore = 9
        styles["Heading2"].spaceBefore = 7
        styles["Heading3"].spaceBefore = 5

        # Colors
        for style_name in ["Title", "Heading1", "Heading2", "Heading3"]:
            styles[style_name].textColor = self.NAVY_BLUE

        return styles

    def _add_logo(self, canvas, doc):
        """Add logo to each page of the document."""
        if not self.logo_path.exists():
            print(f"Logo not found at {self.logo_path}")
            return

        try:
            x = doc.pagesize[0] - doc.rightMargin - self.LOGO_WIDTH
            y = doc.pagesize[1] - doc.topMargin - self.LOGO_HEIGHT

            canvas.drawImage(
                str(self.logo_path),
                x, y,
                width=self.LOGO_WIDTH,
                height=self.LOGO_HEIGHT,
                preserveAspectRatio=True,
                mask='auto'
            )
        except Exception as e:
            print(f"Error adding logo: {str(e)}")

    def _create_document(self) -> SimpleDocTemplate:
        """Create and configure the PDF document."""
        doc = SimpleDocTemplate(self.filename, pagesize=LETTER)

        # Create custom page template with logo
        frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height)
        template = PageTemplate(
            id='main_template',
            frames=[frame],
            onPage=self._add_logo
        )
        doc.addPageTemplates([template])

        return doc

    @staticmethod
    def _replace_figure_placeholders(text: str, chart_metadata: List[Dict[str, str]]) -> str:
        """Replace figure placeholders with actual image references."""

        def replacement(match):
            chart_id = match.group(1)
            for item in chart_metadata:
                if item["id"] == chart_id and os.path.exists(item["path"]):
                    return f"![{chart_id}]({item['path']})"
            return f"[Missing chart: {chart_id}]"

        return re.sub(r"\[\[FIGURE:([a-zA-Z0-9_\-]+)\]\]", replacement, text)

    def _process_markdown_formatting(self, text: str) -> str:
        """Process markdown-style formatting for bold text and other styles."""
        # Handle bold text: **text** or __text__
        text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
        text = re.sub(r'__(.*?)__', r'<b>\1</b>', text)

        # Handle italic text: *text* or _text_
        # Be careful not to match bold patterns
        text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<i>\1</i>', text)
        text = re.sub(r'(?<!_)_(?!_)(.+?)(?<!_)_(?!_)', r'<i>\1</i>', text)

        # Handle inline code: `code`
        text = re.sub(r'`([^`]+)`', r'<font face="Courier">\1</font>', text)

        return text

    def _extract_images_from_text(self, content: str) -> List[Tuple[str, str, str]]:
        """Extract image references from markdown-style text.

        Returns:
            List of tuples: (before_text, alt_text, image_path)
        """
        img_pattern = re.compile(r'!\[(.*?)\]\((.*?)\)')
        parts = []
        last_end = 0

        for match in img_pattern.finditer(content):
            # Text before the image
            before_text = content[last_end:match.start()]
            alt_text = match.group(1)
            img_path = match.group(2)

            parts.append((before_text, alt_text, img_path))
            last_end = match.end()

        # Don't forget the text after the last image
        if last_end < len(content):
            parts.append((content[last_end:], "", ""))

        # If no images found, return the whole content
        if not parts:
            parts.append((content, "", ""))

        return parts

    def _create_image_element(self, img_path: str, alt_text: str) -> List:
        """Create image element with optional caption."""
        elements = []

        try:
            if os.path.exists(img_path):
                img = Image(
                    img_path,
                    width=self.IMAGE_WIDTH,
                    height=self.IMAGE_HEIGHT,
                    kind='proportional'
                )
                elements.append(img)
                elements.append(Spacer(1, 12))

                # Add caption if available
                if alt_text.strip():
                    caption = Paragraph(f"<i>{alt_text}</i>", self.styles["Italic"])
                    elements.append(caption)
                    elements.append(Spacer(1, 12))
            else:
                error_msg = Paragraph(
                    f"[Image not found: {img_path}]",
                    self.styles["BodyText"]
                )
                elements.append(error_msg)
                elements.append(Spacer(1, 6))

        except Exception as e:
            error_msg = Paragraph(
                f"[Error loading image: {str(e)}]",
                self.styles["BodyText"]
            )
            elements.append(error_msg)
            elements.append(Spacer(1, 6))

        return elements

    def _process_content(self, content: str, chart_metadata: List[Dict[str, str]]) -> List:
        """Process content with support for images and text formatting."""
        content = self._replace_figure_placeholders(content, chart_metadata)
        elements = []

        # Extract images and text parts
        parts = self._extract_images_from_text(content)

        for before_text, alt_text, img_path in parts:
            # Process text before image
            if before_text.strip():
                # Split into paragraphs
                paragraphs = before_text.strip().split('\n')
                for para in paragraphs:
                    if para.strip():
                        # Apply markdown formatting
                        formatted_text = self._process_markdown_formatting(para.strip())
                        elements.append(Paragraph(formatted_text, self.styles["BodyText"]))
                        elements.append(Spacer(1, 6))

            # Add image if path exists
            if img_path:
                elements.extend(self._create_image_element(img_path, alt_text))

        return elements

    def _add_section(self, story: List, section: Dict, level: int = 0,
                     chart_metadata: List[Dict[str, str]] = None):
        """Recursively add sections to the story."""
        chart_metadata = chart_metadata or []

        # Choose heading style based on level
        heading_styles = [
            self.styles["Heading1"],
            self.styles["Heading2"],
            self.styles["Heading3"]
        ]
        heading_style = heading_styles[min(level, 2)]

        # Add heading with markdown formatting support
        heading_text = self._process_markdown_formatting(section["heading"])
        story.append(Paragraph(heading_text, heading_style))

        # Process content
        content_text = section.get("content", "")
        if content_text:
            content_elements = self._process_content(content_text, chart_metadata)
            story.extend(content_elements)

        # Handle bullet points
        bullets = section.get("bullet_points", [])
        if bullets:
            bullet_items = []
            for bullet in bullets:
                # Apply markdown formatting to bullet points
                formatted_bullet = self._process_markdown_formatting(bullet)
                bullet_items.append(
                    ListItem(
                        Paragraph(formatted_bullet, self.styles["BodyText"]),
                        leftIndent=20
                    )
                )

            story.append(
                ListFlowable(
                    bullet_items,
                    bulletType='bullet',
                    leftIndent=10,
                    bulletIndent=5
                )
            )
            story.append(Spacer(1, 6))

        # Process subsections
        for subsection in section.get("subsections", []):
            self._add_section(story, subsection, level + 1, chart_metadata)

    def _add_glossary(self, story: List, glossary: Dict):
        """Add glossary section to the document."""
        if not glossary:
            return

        story.append(Paragraph("Glossary", self.styles["Heading1"]))
        story.append(Spacer(1, 6))

        for term, definition in glossary.items():
            formatted_term = self._process_markdown_formatting(term)
            formatted_def = self._process_markdown_formatting(definition)
            entry = Paragraph(f"<b>{formatted_term}</b>: {formatted_def}", self.styles["BodyText"])
            story.append(entry)
            story.append(Spacer(1, 4))

    def _add_sources(self, story: List, sources: List[Dict]):
        """Add sources section to the document."""
        if not sources:
            return

        story.append(Paragraph("Sources", self.styles["Heading1"]))
        story.append(Spacer(1, 6))

        for src in sources:
            src_text = ", ".join([f"{k}: {v}" for k, v in src.items()])
            formatted_src = self._process_markdown_formatting(src_text)
            story.append(Paragraph(formatted_src, self.styles["BodyText"]))
            story.append(Spacer(1, 4))

    def _parse_content(self, content: str) -> Tuple[bool, Optional[Dict], str]:
        """Parse content as JSON AST or plain text.

        Returns:
            Tuple of (is_json, parsed_data, clean_content)
        """
        raw_text = content.strip()

        # Remove code block markers if present
        if raw_text.startswith("```json"):
            raw_text = raw_text[len("```json"):].strip()
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3].strip()

        try:
            parsed = json.loads(raw_text)
            return True, parsed, raw_text
        except json.JSONDecodeError:
            return False, None, content

    def generate(self, content: str, chart_metadata: List[Dict[str, str]] = None) -> str:
        """Generate the PDF report from content.

        Args:
            content: The content to convert to PDF (JSON AST or plain text)
            chart_metadata: List of chart metadata for figure replacement

        Returns:
            Success or error message
        """
        chart_metadata = chart_metadata or []

        try:
            # Parse content
            is_json, parsed_data, clean_content = self._parse_content(content)

            # Create document
            doc = self._create_document()
            story = []

            if is_json and parsed_data:
                # JSON AST mode
                # Add title
                title = parsed_data.get("title", "Untitled Report")
                formatted_title = self._process_markdown_formatting(title)
                story.append(Spacer(1, 64))
                story.append(Paragraph(f"<b>{formatted_title}</b>", self.styles["Title"]))
                story.append(Spacer(1, 12))

                # Add sections
                for section in parsed_data.get("sections", []):
                    self._add_section(story, section, chart_metadata=chart_metadata)

                # Add glossary and sources
                self._add_glossary(story, parsed_data.get("glossary"))
                self._add_sources(story, parsed_data.get("sources"))

            else:
                # Plain text mode
                story.extend(self._process_content(clean_content, chart_metadata))

            # Build the PDF
            doc.build(story)
            return f"Document saved successfully as PDF to '{self.filename}'."

        except Exception as e:
            return f"Error saving document: {str(e)}"


def save_to_pdf(content: str, filename: str = "report.pdf",
                chart_metadata: List[Dict[str, str]] = None) -> str:
    """Convenience function to maintain backward compatibility.

    Args:
        content: The content to convert to PDF
        filename: Output filename
        chart_metadata: List of chart metadata for figure replacement

    Returns:
        Success or error message
    """
    generator = PDFReportGenerator(filename)
    return generator.generate(content, chart_metadata or [])