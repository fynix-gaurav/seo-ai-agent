# backend/app/agents/writer_editor_agent.py
# This file defines the Writer-Editor agent using LangGraph and LangChain.

import os
from typing import List, TypedDict

# LangChain and LangGraph Imports
from langchain.prompts import ChatPromptTemplate
from langchain_anthropic import ChatAnthropic
from langchain_core.output_parsers import PydanticOutputParser, StrOutputParser
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

# Pydantic V1 Imports - This is crucial for compatibility
from pydantic.v1 import BaseModel, Field

# --- Configuration ---
MAX_REVISIONS = 2
# We will define our models and prompts directly here for clarity.
# Later, we can refactor them into config/prompt files if needed.
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")


# --- 1. Define the State and Pydantic Models (V1 for LangGraph) ---

class EditorDecision(BaseModel):
    """The decision and feedback from the editor node."""
    decision: str = Field(description="The verdict on the content. Must be either 'APPROVED' or 'REVISE'.")
    feedback: str = Field(description="Constructive, actionable feedback for the writer if the decision is 'REVISE'.")

class ArticleSection(BaseModel):
    """Represents a single written section of the article."""
    h2: str
    content: str

class ArticleDraft(BaseModel):
    """Represents the full article draft being written."""
    h1: str
    sections: List[ArticleSection] = []

class GraphState(TypedDict):
    """Represents the state of our graph, the agent's memory."""
    original_outline: dict
    article_draft: ArticleDraft
    current_section_index: int
    current_section_content: str
    editor_feedback: EditorDecision
    revision_attempts: int


# --- 2. Define the Writer's Logic ---

# We'll use a cost-effective but powerful model as our workhorse writer.
writer_llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.7, api_key=OPENAI_API_KEY)

writer_prompt_template = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are an expert B2B content writer and subject matter expert. Your task is to write a comprehensive, engaging, and authoritative section for a larger article. The tone should be professional, clear, and credible, tailored for a B2B audience.",
        ),
        (
            "user",
            """Please write the content for the following section of the article titled "{h1}".

**Section to Write:**
## {h2_title}

**Key Topics to Cover in this section (H3s):**
{h3_topics}

**Instructions:**
- Write a detailed and informative piece of content for the section.
- Ensure you cover all the key topics listed above.
- The writing must be original, engaging, and provide real value to the reader.
- Do not write an introduction or conclusion for the entire article, only focus on this specific section.
- Do not repeat the H2 or H3 titles in your writing.

**Editor Feedback (for revisions):**
{feedback}
""",
        ),
    ]
)

# The writer chain simply combines the prompt, model, and a basic string output parser.
writer_chain = writer_prompt_template | writer_llm | StrOutputParser()


def writer_node(state: GraphState):
    """
    The "Writer" node. Takes the current section and writes content for it.
    """
    print("--- ✍️ WRITER NODE ---")

    # Get the current section to write from the agent's memory (the state)
    outline = state["original_outline"]
    section_index = state["current_section_index"]
    section_to_write = outline["sections"][section_index]
    
    h1 = outline["h1"]
    h2_title = section_to_write["h2"]
    h3_topics = "\n".join([f"- {h3['h3']}" for h3 in section_to_write["h3s"]])

    # Get feedback if this is a revision attempt
    feedback_obj = state.get("editor_feedback")
    feedback = (
        feedback_obj.feedback
        if feedback_obj
        else "No feedback yet. This is the first attempt."
    )

    # Increment the revision counter
    state["revision_attempts"] += 1
    
    # Invoke the writer chain to generate the content
    generated_content = writer_chain.invoke(
        {"h1": h1, "h2_title": h2_title, "h3_topics": h3_topics, "feedback": feedback}
    )
    
    # Update the state with the new content and clear old feedback
    return {
        "current_section_content": generated_content,
        "editor_feedback": None # Reset feedback for the next editor review
    }


# --- 3. Define the Editor's Logic ---

# We use a strategic model for the high-reasoning task of editing.
# We'll use Haiku for cost-effectiveness, with a fallback to OpenAI.
if ANTHROPIC_API_KEY:
    editor_llm = ChatAnthropic(
        model="claude-3-haiku-20240307", temperature=0, api_key=ANTHROPIC_API_KEY
    )
else:
    editor_llm = ChatOpenAI(
        model="gpt-3.5-turbo", temperature=0, api_key=OPENAI_API_KEY
    )

# The parser ensures the editor's output is always a structured object we can trust.
editor_parser = PydanticOutputParser(pydantic_object=EditorDecision)

editor_prompt_template = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a meticulous, world-class editor and SEO strategist. Your task is to review a piece of content written by an AI writer and decide if it meets our quality standards. Your response MUST be a JSON object adhering to the provided schema. Do not include any other text or explanations.",
        ),
        (
            "user",
            """**Article Topic:** "{h1}"
**Section Being Reviewed:** "## {h2_title}"

**Content to Review:**
<content>
{content_to_review}
</content>

**Evaluation Criteria:**
1.  **Clarity & Readability:** Is the content clear, concise, and easy for a B2B audience to understand?
2.  **Accuracy:** Is the information factually correct and credible?
3.  **Completeness:** Does the content adequately cover all the required sub-topics ({h3_topics})?
4.  **Tone:** Is the tone authoritative, professional, and confident?

**Your Task:**
Based on the criteria, make a decision.
- If the content is excellent and meets all criteria, decide "APPROVED".
- If the content has issues, decide "REVISE" and provide specific, actionable feedback for the writer to improve the content.

<output_instructions>
{format_instructions}
</output_instructions>
""",
        ),
    ]
)

# The editor chain combines the prompt, model, and the structured output parser.
editor_chain = editor_prompt_template | editor_llm | editor_parser


def editor_node(state: GraphState):
    """
    The "Editor" node. Reviews the content and provides a structured decision.
    """
    print("--- 🧐 EDITOR NODE ---")

    # Get the necessary context from the agent's memory (the state)
    outline = state["original_outline"]
    section_index = state["current_section_index"]
    section_to_review = outline["sections"][section_index]
    
    h1 = outline["h1"]
    h2_title = section_to_review["h2"]
    h3_topics = ", ".join([h3["h3"] for h3 in section_to_review["h3s"]])
    content_to_review = state["current_section_content"]

    # Invoke the editor chain to get the structured decision
    decision = editor_chain.invoke(
        {
            "h1": h1,
            "h2_title": h2_title,
            "h3_topics": h3_topics,
            "content_to_review": content_to_review,
            "format_instructions": editor_parser.get_format_instructions(),
        }
    )
    
    # Update the state with the editor's feedback
    return {"editor_feedback": decision}

# In backend/app/agents/writer_editor_agent.py

# --- 4. Define Conditional Edge Logic ---

def should_continue(state: GraphState):
    """
    The agent's "brain". This function decides the next step based on the state.
    """
    print("--- 🤔 DECISION ---")
    editor_decision = state["editor_feedback"]

    # If the editor requests a revision and we haven't exceeded the limit,
    # loop back to the writer.
    if (
        editor_decision.decision == "REVISE"
        and state["revision_attempts"] < MAX_REVISIONS
    ):
        print(f"Decision: Revision attempt {state['revision_attempts']}. Sending back to writer.")
        return "writer"

    # If the content is approved (or we're out of revisions),
    # add the content to the final draft.
    print("Decision: Content APPROVED. Appending to draft.")
    outline = state["original_outline"]
    section_index = state["current_section_index"]
    approved_section_outline = outline["sections"][section_index]
    
    # Create an ArticleSection object with the approved content
    approved_section = ArticleSection(
        h2=approved_section_outline['h2'],
        content=state["current_section_content"]
    )
    state["article_draft"].sections.append(approved_section)

    # Check if there are more sections left to write.
    if state["current_section_index"] < len(outline["sections"]) - 1:
        print("Decision: Moving to the next section.")
        # Increment the index to move to the next section
        state["current_section_index"] += 1
        # Reset the revision counter for the new section
        state["revision_attempts"] = 0
        return "writer"
    else:
        # If all sections are done, end the process.
        print("Decision: All sections are complete. Finishing.")
        return END

# --- 5. Wire up and compile the Graph ---

# Initialize the state graph
workflow = StateGraph(GraphState)

# Add the nodes (our "workers")
workflow.add_node("writer", writer_node)
workflow.add_node("editor", editor_node)

# Set the entry point for the graph
workflow.set_entry_point("writer")

# The writer always sends its work to the editor
workflow.add_edge("writer", "editor")

# The editor's decision is routed by our conditional logic
workflow.add_conditional_edges(
    "editor",
    should_continue,
    {
        "writer": "writer", # Loop back to writer for revisions or the next section
        END: END # Finish the graph
    }
)

# Compile the graph into a runnable application
app = workflow.compile()