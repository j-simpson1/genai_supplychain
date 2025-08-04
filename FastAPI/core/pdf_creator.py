import json
import re
import os
from typing import List, Dict
from pathlib import Path

from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.colors import Color
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import LETTER
from reportlab.platypus.frames import Frame
from reportlab.platypus.doctemplate import PageTemplate
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, ListFlowable, ListItem


def save_to_pdf(content: str, filename: str = "report.pdf", chart_metadata: List[Dict[str, str]] = []) -> str:
    """Save the current document as a PDF file."""

    if not filename.endswith(".pdf"):
        filename += ".pdf"

    try:
        # Try to parse as JSON AST
        raw_text = content.strip()

        if raw_text.startswith("```json"):
            raw_text = raw_text[len("```json"):].strip()
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3].strip()

        try:
            parsed = json.loads(raw_text)
            is_json_ast = True
        except json.JSONDecodeError:
            is_json_ast = False

        # Generate PDF
        doc = SimpleDocTemplate(filename, pagesize=LETTER)
        styles = getSampleStyleSheet()
        styles["Title"].fontSize = 20
        styles["Heading1"].fontSize = 16
        styles["Heading2"].fontSize = 14
        styles["Heading3"].fontSize = 12
        styles["Heading1"].spaceBefore = 9
        styles["Heading2"].spaceBefore = 7
        styles["Heading3"].spaceBefore = 5
        navy_blue = Color(19 / 255, 52 / 255, 92 / 255)  # Convert RGB to 0-1 scale
        styles["Title"].textColor = navy_blue
        styles["Heading1"].textColor = navy_blue
        styles["Heading2"].textColor = navy_blue
        styles["Heading3"].textColor = navy_blue

        # Create a function to add the logo to each page
        def add_logo(canvas, doc):

            BASE_DIR = Path(__file__).resolve().parent.parent
            LOGO_PATH = BASE_DIR / "static" / "Alvarez_and_Marsal.png"

            logo_path = str(LOGO_PATH)
            try:
                width = 1.5 * inch
                height = 0.75 * inch
                x = doc.pagesize[0] - doc.rightMargin - width
                y = doc.pagesize[1] - doc.topMargin - height
                canvas.drawImage(
                    logo_path,
                    x,
                    y,
                    width=width,
                    height=height,
                    preserveAspectRatio=True,
                    mask='auto'
                )
            except Exception as e:
                print(f"Error adding logo: {str(e)}")

        # Create a custom page template with the logo
        frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height)
        template = PageTemplate(id='main_template', frames=[frame], onPage=add_logo)
        doc.addPageTemplates([template])

        story = []

        def replace_figure_placeholders(text, chart_metadata):
            def replacement(match):
                chart_id = match.group(1)
                for item in chart_metadata:
                    if item["id"] == chart_id and os.path.exists(item["path"]):
                        return f"![{chart_id}]({item['path']})"
                return f"[Missing chart: {chart_id}]"

            return re.sub(r"\[\[FIGURE:([a-zA-Z0-9_\-]+)\]\]", replacement, text)

        # Function to process content and extract images
        def process_content(content, chart_metadata):

            content = replace_figure_placeholders(content, chart_metadata)

            elements = []
            # Match markdown image syntax: ![alt text](path/to/image.png)
            img_pattern = re.compile(r'!\[(.*?)\]\((.*?)\)')

            # Split by image references
            parts = img_pattern.split(content)

            for i in range(0, len(parts)):
                # Text parts (even indices)
                if i % 3 == 0 and parts[i].strip():
                    paragraphs = parts[i].strip().split('\n')
                    for para in paragraphs:
                        if para.strip():
                            elements.append(Paragraph(para.strip(), styles["BodyText"]))
                            elements.append(Spacer(1, 6))

                # Image parts (paths are at indices 1, 4, 7, etc.)
                if i % 3 == 2:
                    img_path = parts[i]
                    try:
                        if os.path.exists(img_path):
                            img = Image(img_path, width=3.75 * inch, height=2.75 * inch, kind='proportional')
                            elements.append(img)
                            elements.append(Spacer(1, 12))
                            # Add caption if available (at indices 0, 3, 6, etc.)
                            if i > 0 and parts[i - 1].strip():
                                elements.append(Paragraph(f"<i>{parts[i - 1]}</i>", styles["Italic"]))
                                elements.append(Spacer(1, 12))
                    except Exception as e:
                        elements.append(Paragraph(f"[Error loading image: {img_path}]", styles["BodyText"]))
                        elements.append(Spacer(1, 6))

            return elements

        if is_json_ast:
            # Add title
            title = parsed.get("title", "Untitled Report")
            story.append(Spacer(1, 64))
            story.append(Paragraph(f"<b>{title}</b>", styles["Title"]))
            story.append(Spacer(1, 12))

            def add_section(section, level=0):
                # Choose heading style based on level
                if level == 0:
                    heading_style = styles["Heading1"]
                elif level == 1:
                    heading_style = styles["Heading2"]
                else:
                    heading_style = styles["Heading3"]

                # Heading
                story.append(Paragraph(section["heading"], heading_style))

                # Process content with image handling
                content_text = section.get("content", "")
                content_elements = process_content(content_text, chart_metadata)
                story.extend(content_elements)

                # Handle bullet points
                bullets = section.get("bullet_points", [])
                if bullets:
                    bullet_items = [
                        ListItem(Paragraph(b, styles["BodyText"]), leftIndent=20)
                        for b in bullets
                    ]
                    story.append(
                        ListFlowable(
                            bullet_items,
                            bulletType='bullet',
                            leftIndent=10,
                            bulletIndent=5
                        )
                    )
                    story.append(Spacer(1, 6))

                # Subsections
                for sub in section.get("subsections", []):
                    add_section(sub, level + 1)

            # Add each section
            for s in parsed.get("sections", []):
                add_section(s)

            # Optionally, handle glossary and sources
            glossary = parsed.get("glossary")
            if glossary:
                story.append(Paragraph("Glossary", styles["Heading1"]))
                story.append(Spacer(1, 6))
                for term, definition in glossary.items():
                    story.append(Paragraph(f"<b>{term}</b>: {definition}", styles["BodyText"]))
                    story.append(Spacer(1, 4))

            sources = parsed.get("sources")
            if sources:
                story.append(Paragraph("Sources", styles["Heading1"]))
                story.append(Spacer(1, 6))
                for src in sources:
                    src_text = ", ".join([f"{k}: {v}" for k, v in src.items()])
                    story.append(Paragraph(src_text, styles["BodyText"]))
                    story.append(Spacer(1, 4))

        else:
            # Plain text mode with image handling
            story.extend(process_content(content, chart_metadata))

        doc.build(story)
        return f"Document saved successfully as PDF to '{filename}'."

    except Exception as e:
        return f"Error saving document: {str(e)}"