from typing import Annotated, Sequence, TypedDict
from dotenv import load_dotenv
import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import squarify

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_community.tools import TavilySearchResults

import json
import re
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.colors import Color
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import LETTER
from reportlab.platypus.frames import Frame
from reportlab.platypus.doctemplate import PageTemplate
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image

from FastAPI.data.auto_parts.tecdoc import fetch_manufacturers

load_dotenv()

# Global variable to store document content
document_content = ""


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]


@tool
def update(content: str) -> str:
    """Updates the document with the provided content."""
    global document_content
    document_content = content
    return f"Document has been updated successfully! The current content is:\n{document_content}"


@tool
def save(filename: str) -> str:
    """Save the current document as a PDF file."""
    global document_content

    if not filename.endswith(".pdf"):
        filename += ".pdf"

    try:
        # Try to parse as JSON AST
        raw_text = document_content.strip()

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
        styles["Heading2"].fontSize = 12
        styles["Heading3"].fontSize = 10
        navy_blue = Color(19 / 255, 52 / 255, 92 / 255)  # Convert RGB to 0-1 scale
        styles["Title"].textColor = navy_blue
        styles["Heading1"].textColor = navy_blue
        styles["Heading2"].textColor = navy_blue
        styles["Heading3"].textColor = navy_blue

        # Create a function to add the logo to each page
        def add_logo(canvas, doc):
            import os
            logo_path = os.path.abspath("Alvarez_and_Marsal.png")
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

        # Function to process content and extract images
        def process_content(content):
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
                            img = Image(img_path, width=4 * inch, height=3 * inch, kind='proportional')
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
                story.append(Spacer(1, 6))

                # Process content with image handling
                content_elements = process_content(section["content"])
                story.extend(content_elements)

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
            story.extend(process_content(document_content))

        doc.build(story)
        return f"Document saved successfully as PDF to '{filename}'."

    except Exception as e:
        return f"Error saving document: {str(e)}"


# @tool
# def retrieve_manufacturers():
#     """Calls the API retrieving the manufacturers by calling the TecDoc API."""
#     result = fetch_manufacturers()
#     brands = [m['brand'] for m in result.get('manufacturers', [])]
#     for brand in brands:
#         print(brand)
#     return f"Retrieved {len(brands)} manufacturers"


tools = [update, save]

# Models
model = ChatOpenAI(model="gpt-4o").bind_tools(tools)
drafting_model = ChatOpenAI(model="gpt-4o")
search_tool = TavilySearchResults(api_key=os.environ["TAVILY_API_KEY"])

def get_component_overview():
    manufacturer_df = pd.read_csv("dummy_data/manufacturers_dummy_data.csv")
    models_df = pd.read_csv("dummy_data/models_dummy_data.csv")
    vehicle_df = pd.read_csv("dummy_data/vehicle_dummy_data.csv")
    parts_df = pd.read_csv("dummy_data/parts_dummy_data.csv")
    articles_df = pd.read_csv("dummy_data/article_dummy_data.csv")

    component_overview = (
        f"Manufacturer: {manufacturer_df['description']}, "
        f"Model: {models_df['description']}, "
        f"Engine Type: {vehicle_df['description']}, "
        f"Component: Braking System."
    )

    selected_parts_df = parts_df[['productGroupId', 'description', 'categoryId']]

    return component_overview, selected_parts_df, articles_df


get_component_overview()


def generate_visualisations(csv_path: str = "article_dummy_data.csv") -> list:
    """Generate visualisations and return list of image paths."""
    df = pd.read_csv(csv_path)
    df['priceSource'] = df['priceSource'].astype(str)
    sns.set(style="whitegrid")
    image_paths = []

    output_dir = "visualisations"
    os.makedirs(output_dir, exist_ok=True)
    print("Saving visualisations to:", os.path.abspath(output_dir))

    # Box Plot
    plt.figure(figsize=(10, 6))
    sns.boxplot(
        x="countryOfOrigin",
        y="price",
        hue="countryOfOrigin",
        data=df,
        palette="Set2",
        legend=False
    )
    plt.title("Price Distribution by Country of Origin")
    plt.xlabel("Country of Origin")
    plt.ylabel("Price (€)")
    plt.tight_layout()
    boxplot_path = os.path.join(output_dir, "boxplot_price_by_country.png")
    plt.savefig(boxplot_path)
    plt.close()
    image_paths.append(boxplot_path)

    # Bar Chart
    avg_price_supplier = df.groupby("supplierId")["price"].mean().reset_index()
    plt.figure(figsize=(12, 6))
    sns.barplot(
        x="supplierId",
        y="price",
        hue="supplierId",
        data=avg_price_supplier,
        palette="viridis",
        legend=False
    )
    plt.title("Average Price per Supplier")
    plt.xlabel("Supplier ID")
    plt.ylabel("Average Price (€)")
    plt.tight_layout()
    bar_chart_path = os.path.join(output_dir, "bar_chart_avg_price_per_supplier.png")
    plt.savefig(bar_chart_path)
    plt.close()
    image_paths.append(bar_chart_path)

    # Treemap
    product_agg = df.groupby("articleProductName")["price"].sum().reset_index()
    labels = [
        f"{row['articleProductName']}\n€{row['price']:.2f}"
        for _, row in product_agg.iterrows()
    ]
    sizes = product_agg["price"].values
    plt.figure(figsize=(12, 8))
    squarify.plot(
        sizes=sizes,
        label=labels,
        alpha=0.8
    )
    plt.title("Treemap of Total Price by Product Type")
    plt.axis('off')
    plt.tight_layout()
    treemap_path = os.path.join(output_dir, "treemap_product_types.png")
    plt.savefig(treemap_path)
    plt.close()
    image_paths.append(treemap_path)

    return image_paths


def researcher(state: AgentState) -> AgentState:
    """Research node - gathers information about tariffs and supply chains"""

    print("\n===== Starting Research Phase... =====\n")

    query = (
        "Find the most recent and relevant news articles (from the past 6 months) about tariffs, sanctions, inflation, "
        "and their impact on global automotive supply chains. Focus on major developments, policy changes, or disruptions. "
        "For each article, provide:\n"
        "- Publication date\n"
        "- Headline\n"
        "- 1-2 sentence summary\n"
        "- Source URL\n"
        "Return 3-5 key articles in bullet point format."
    )

    # Use search tool directly
    search_results = search_tool.invoke({"query": query})

    # Create a prompt for the model to summarize the results
    summary_prompt = f"""
    Based on the following search results, create a summary about recent news regarding tariffs, sanctions, inflation, and automotive supply chains. 
    Summarize in 3-5 bullet points with publication dates and URLs where available.

    Search Results:
    {search_results}
    """

    # Get summary from the model
    summary_response = drafting_model.invoke([HumanMessage(content=summary_prompt)])
    summary = summary_response.content

    # Log the research results
    print(f"{summary}")
    print("\n===== End of Research =====\n")

    # Create AI message with the research summary
    ai_msg = AIMessage(content=summary)

    return {
        "messages": [
            HumanMessage(content=query),
            ai_msg
        ]
    }

def initial_drafter(state: AgentState) -> AgentState:
    """Draft the initial report based on research"""
    print("\n===== Creating initial draft... =====\n")

    # Get the research summary from the last AI message
    research_summary = ""
    for msg in reversed(state.get("messages", [])):
        if isinstance(msg, AIMessage):
            research_summary = msg.content
            break

    component_overview, selected_parts_df, articles_df = get_component_overview()

    # Generate visualisations and get Markdown links
    image_paths = generate_visualisations("dummy_data/article_dummy_data.csv")
    markdown_links = [f"![]({path})" for path in image_paths]
    visualisations_md = "\n\n".join(markdown_links)

    system_prompt = SystemMessage(content=f"""
    You are a report generator. Create a draft of a report on recent news regarding tariffs, sanctions, inflation,
    and global supply chains, analyzing the impact on automotive supply chains focusing on the component chosen.

    **IMPORTANT:**
    Instead of plain text, return the report as a JSON Abstract Syntax Tree (AST).
    The JSON structure should have the following format:

    {{
      "title": "<Report Title>",
      "sections": [
        {{
          "heading": "<Section Heading>",
          "content": "<Plain text or markdown content>",
          "subsections": [
            {{
              "heading": "<Subsection Heading>",
              "content": "<Plain text or markdown content>"
            }}
          ]
        }}
      ]
    }}
    
    Section Order:
    1. Executive Summary
    2. Component Overview
    3. Other sections in logical order
    
    Ensure that all report content is included in this JSON AST format and the output is a as raw JSON, not inside a 
    code block or Markdown fencing.

    Add a dedicated section titled 'Component Overview' with the following details:
    {component_overview}

    Use the following research summary as your main source:
    {research_summary}

    In a section titled 'Supply Chain Visualisations', include the following visualisations:
    {visualisations_md}
    """)

    user_message = HumanMessage(content="Please generate the draft report now.")
    all_messages = [system_prompt, user_message]

    response = drafting_model.invoke(all_messages)

    # Log the draft creation
    print(response.content)
    print("\n===== End of initial draft =====\n")

    global document_content
    document_content = response.content

    return {
        "messages": [
            user_message,
            AIMessage(content=response.content)
        ]
    }


def report_critic(state: AgentState) -> AgentState:
    """Evaluate and provide feedback on the draft report"""
    print("\n===== Evaluating report quality... =====")

    global document_content

    system_prompt = SystemMessage(content="""
    You are a professional report critic. Evaluate the following report on:
    1. Clarity and readability
    2. Completeness of information
    3. Logical structure and flow
    4. Factual accuracy and sourcing (NOTE: Do NOT comment on dates - assume all dates are correct)
    5. Professional formatting

    IMPORTANT: Do NOT flag dates or temporal references as issues. Assume all dates in the report are accurate.

    Provide specific, actionable feedback and end with a quality score (1-10).
    Format your final line as: "QUALITY SCORE: X/10"
    If score is below 7, suggest specific improvements.
    """)

    critique_message = HumanMessage(content=f"Please evaluate this report:\n\n{document_content}")
    response = drafting_model.invoke([system_prompt, critique_message])

    print(f"\nREPORT EVALUATION:\n\n{response.content}")

    return {"messages": [critique_message, response]}

def auto_reviser(state: AgentState) -> AgentState:
    """Automatically revise the report based on critic feedback"""
    print("\n\n===== Auto-revising report based on feedback... =====")

    global document_content

    # Get critic feedback
    critic_feedback = ""
    for msg in reversed(state.get("messages", [])):
        if isinstance(msg, AIMessage) and ("QUALITY SCORE:" in msg.content or "feedback" in msg.content.lower()):
            critic_feedback = msg.content
            break

    system_prompt = SystemMessage(content=f"""
    You are a report reviser. Improve the following report based on the critic's feedback.
    Make specific improvements addressing the feedback while maintaining the core content.

    CRITICAL INSTRUCTIONS:
    - PRESERVE ALL DATES EXACTLY as they appear in the original report
    - Do NOT change any dates, years, or temporal references
    - If dates seem unusual, assume they are correct and leave them unchanged
    - Focus only on improving content quality, structure, and clarity
    - Return the revised report in the same JSON AST format as the input.
    - Output raw JSON only, without Markdown code fences or additional commentary.

    Critic Feedback:
    {critic_feedback}

    Current Report:
    {document_content}
    """)

    revision_message = HumanMessage(content="Please revise the report based on the feedback.")
    response = drafting_model.invoke([system_prompt, revision_message])

    print(f"\nREVISED REPORT:\n\n{response.content}")

    update_result = update(response.content)

    return {
        "messages": [
            revision_message,
            AIMessage(
                content=response.content,
                tool_calls=[
                    {
                        "name": "update",
                        "args": {"content": response.content},
                        "id": "revision_update_call"
                    }
                ]
            ),
            ToolMessage(
                tool_call_id="revision_update_call",
                content=update_result
            )
        ]
    }

def user_input_node(state: AgentState) -> AgentState:
    """Interactive agent for document editing"""
    print("\n===== Ready for user interaction... =====")

    system_prompt = SystemMessage(content=f"""
        You are Drafter, a helpful writing assistant. You help users update and modify documents.

        IMPORTANT INSTRUCTIONS:
        - Unless the user specifically asks to change or remove other sections, preserve existing content exactly.
        - When requested, integrate only the requested changes and indicate which section was changed.
        - Output the complete updated document text (including unchanged parts) after applying edits.
        - If the user only asks to review or comment, do not make changes—only provide comments.

        The current document content is:
        {document_content}
        """)

    # Get user input
    user_input = input("\nWhat would you like to do with the document? ")
    print(f"\nUSER: {user_input}")

    user_message = HumanMessage(content=user_input)

    # Get all messages and add the system prompt
    all_messages = [system_prompt] + list(state.get("messages", [])) + [user_message]

    # Get response from the model
    response = model.invoke(all_messages)

    # Log the interaction
    print(f"\nAI: {response.content}")
    if hasattr(response, "tool_calls") and response.tool_calls:
        print(f"🔧 USING TOOLS: {[tc['name'] for tc in response.tool_calls]}")

    return {"messages": [user_message, response]}


def should_continue(state: AgentState) -> str:
    """Determine if we should continue or end the conversation."""
    messages = state.get("messages", [])

    if not messages:
        return "continue"

    # Check for save tool usage in recent messages
    for message in reversed(messages[-3:]):  # Check last 3 messages
        if isinstance(message, ToolMessage):
            if "saved" in message.content.lower() and "document" in message.content.lower():
                return "end"
        elif isinstance(message, AIMessage) and hasattr(message, 'tool_calls'):
            if any(tc.get('name') == 'save' for tc in message.tool_calls or []):
                return "end"

    return "continue"

def needs_revision(state: AgentState) -> str:
    """Determine if the report needs revision based on critic feedback"""
    messages = state.get("messages", [])

    # Get the last critic response
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and "QUALITY SCORE:" in msg.content:
            # Extract score
            try:
                score_line = [line for line in msg.content.split('\n') if 'QUALITY SCORE:' in line][-1]
                score = int(score_line.split(':')[1].split('/')[0].strip())
                print(f"\n📊 Quality Score: {score}/10")

                if score < 7:
                    print("📝 Report needs revision")
                    return "revise"
                else:
                    print("✅ Report quality acceptable")
                    return "proceed"
            except:
                print("⚠️ Could not parse quality score, proceeding to revision")
                return "revise"

    return "revise"

def route_from_tools(state: AgentState) -> str:
    """Route from tools based on context"""
    messages = state.get("messages", [])

    # Check if we should end (save was called)
    for message in reversed(messages[-3:]):
        if isinstance(message, ToolMessage):
            if "saved" in message.content.lower() and "document" in message.content.lower():
                return "end"
        elif isinstance(message, AIMessage) and hasattr(message, 'tool_calls'):
            if any(tc.get('name') == 'save' for tc in message.tool_calls or []):
                return "end"

    # Otherwise continue to revision drafter
    return "continue"


def load_document(filename: str) -> str:
    """Load a document from file"""
    global document_content
    try:
        with open(filename, 'r') as file:
            document_content = file.read()
        print(f"\nDocument loaded from: {filename}")
        return f"Document loaded successfully from '{filename}'."
    except Exception as e:
        return f"Error loading document: {str(e)}"


# Build the graph
def create_graph():
    """Create and compile the LangGraph"""
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("researcher", researcher)
    graph.add_node("report_drafter", initial_drafter)
    graph.add_node("report_critique", report_critic)
    graph.add_node("auto_reviser", auto_reviser)
    graph.add_node("user_input", user_input_node)
    graph.add_node("tools", ToolNode(tools))

    # Set entry point
    graph.set_entry_point("researcher")

    # Add edges
    graph.add_edge("researcher", "report_drafter")
    graph.add_edge("report_drafter", "report_critique")


    # After critique, decide revision or proceed
    graph.add_conditional_edges(
        "report_critique",
        needs_revision,
        {
            "revise": "auto_reviser",
            "proceed": "user_input"
        }
    )

    # Auto reviser goes back to tools to update document
    graph.add_edge("auto_reviser", "report_critique")

    graph.add_conditional_edges(
        "tools",
        route_from_tools,
        {
            "continue": "user_input",
            "end": END
        }
    )

    # Add conditional edges
    graph.add_conditional_edges(
        "user_input",
        lambda state: "tools" if any(
            hasattr(msg, 'tool_calls') and msg.tool_calls
            for msg in state.get("messages", [])[-1:]
        ) else "continue",
        {
            "tools": "tools",
            "continue": "user_input"
        }
    )

    app = graph.compile()

    with open("graph.png", "wb") as f:
        f.write(app.get_graph().draw_mermaid_png())

    return app


def run_document_agent():
    """Main execution function"""
    print("\n***** Starting Document Agent *****")

    # Create the graph
    app = create_graph()

    # Initial state
    state = {"messages": []}

    # Run the graph
    try:
        final_state = app.invoke(state)
        print("\n===== DOCUMENT AGENT COMPLETED =====")
        return final_state
    except Exception as e:
        print(f"\n❌ Error during execution: {e}")
        return None


if __name__ == "__main__":
    # Load initial document if needed
    # load_document('../../exports/parts_data.csv')

    # Run the agent
    run_document_agent()