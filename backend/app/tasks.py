# tasks.py

import os
import json
from typing import List, Optional
from .celery_config import celery_app
from .services import serp_service, scraper_service
from . import crud, schemas, models
from .database import SessionLocal
from .agents.writer_editor_agent import app as writing_agent_app, GraphState, ArticleDraft

from .config import DEV_OPENAI_MODEL, DEV_ANTHROPIC_MODEL, PROD_ANTHROPIC_STRATEGIST_MODEL
from .prompts import (
    TOPIC_GROUPER_SYSTEM_PROMPT,
    TOPIC_GROUPER_USER_PROMPT,
    OUTLINE_ARCHITECT_SYSTEM_PROMPT,
    OUTLINE_ARCHITECT_USER_PROMPT,
    OUTLINE_REFINER_SYSTEM_PROMPT
)

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

@celery_app.task(bind=True)
def generate_outline_task(self, project_id: int, keyword: str, manual_keywords: Optional[List[str]] = None):
    db = SessionLocal()
    try:
        crud.update_project_status(db, project_id=project_id, status=schemas.ProjectStatus.IN_PROGRESS)

        print("Fetching SERP data...")
        serp_data = serp_service.get_serp_results(keyword)
        if "error" in serp_data or "organic" not in serp_data:
            raise ValueError("Failed to fetch SERP data.")

        urls = [result['link'] for result in serp_data.get('organic', [])[:10]]
        scraped_headings = []
        for url in urls:
            # Use our new, targeted function
            headings = scraper_service.scrape_url_for_headings(url)
            if headings:
                scraped_headings.extend(headings)

        scraped_content_for_prompt = "\n".join(scraped_headings)
        print(f"Scraped {len(scraped_headings)} headings from top {len(urls)} URLs.")

        # --- AI Step 1: Topic Grouper (GPT-3.5-Turbo) ---
        print(f"Grouping topics with {DEV_OPENAI_MODEL}o...")
        grouper_parser = PydanticOutputParser(pydantic_object=models.TopicClusterList)
        grouper_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", TOPIC_GROUPER_SYSTEM_PROMPT),
                ("user", TOPIC_GROUPER_USER_PROMPT),
            ]
        )
        # --- MODEL UPDATED TO THE MOST COST-EFFECTIVE OPTION ---
        llm_grouper = ChatOpenAI(model=DEV_OPENAI_MODEL, temperature=0, api_key=OPENAI_API_KEY)
        chain_grouper = grouper_prompt | llm_grouper | grouper_parser
        
        topic_clusters = chain_grouper.invoke({
            "format_instructions": grouper_parser.get_format_instructions(),
            "scraped_content": scraped_content_for_prompt,
            "manual_keywords": ", ".join(manual_keywords) if manual_keywords else "None"
        })

        # --- AI Step 2: Outline Architect (Claude 3 Haiku) ---
        print(f"Architecting outline with Claude {DEV_ANTHROPIC_MODEL}...")
        architect_parser = PydanticOutputParser(pydantic_object=models.SeoOutline)
        architect_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", OUTLINE_ARCHITECT_SYSTEM_PROMPT),
                ("user", OUTLINE_ARCHITECT_USER_PROMPT),
            ]
        )
        
        
        if ANTHROPIC_API_KEY:
            llm_architect = ChatAnthropic(model=DEV_ANTHROPIC_MODEL, temperature=0, api_key=ANTHROPIC_API_KEY)
        else: # Fallback to OpenAI's cheapest
            llm_architect = ChatOpenAI(model=DEV_OPENAI_MODEL, temperature=0, api_key=OPENAI_API_KEY)

        chain_architect = architect_prompt | llm_architect | architect_parser
        
        draft_outline = chain_architect.invoke({
            "format_instructions": architect_parser.get_format_instructions(),
            "keyword": keyword,
            "topic_clusters_json": topic_clusters.model_dump_json()
        })

        # --- NEW AI Step 3: Outline Refiner (Claude 3 Opus) ---
        print(f"Refining outline with {DEV_ANTHROPIC_MODEL}...")
        
        # We reuse the same Pydantic parser
        refiner_parser = architect_parser 
        
        refiner_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", OUTLINE_REFINER_SYSTEM_PROMPT),
                # The user prompt now contains the DRAFT outline
                ("user", """
                 <output_instructions>
                 {format_instructions}
                 </output_instructions>

                 **Primary Keyword:** "{keyword}"

                 <draft_outline>
                 {draft_outline_json}
                 </draft_outline>
                 """),
            ]
        )
        
        # We use our most powerful model for this final strategic task
        llm_refiner = ChatAnthropic(
            model=DEV_ANTHROPIC_MODEL, temperature=0, api_key=ANTHROPIC_API_KEY
        )
        
        chain_refiner = refiner_prompt | llm_refiner | refiner_parser

        # This is now the FINAL, high-quality outline
        final_outline = chain_refiner.invoke(
            {
                "format_instructions": refiner_parser.get_format_instructions(),
                "keyword": keyword,
                "draft_outline_json": draft_outline.model_dump_json(),
            }
        )

        # --- Save the final result ---
        article_title = final_outline.h1
        article_content = final_outline.model_dump_json(indent=2)
        
        crud.create_article_for_project(db, title=article_title, content=article_content, project_id=project_id)
        crud.update_project_status(db, project_id=project_id, status=schemas.ProjectStatus.COMPLETED)
        
        print("Task succeeded. Outline saved to database.")
        return {"status": "SUCCESS", "outline_h1": article_title}

    except Exception as e:
        print(f"Task failed: {e}")
        crud.update_project_status(db, project_id=project_id, status=schemas.ProjectStatus.FAILED)
        raise e
    finally:
        db.close()


@celery_app.task(bind=True)
def generate_full_article_task(self, article_id: int):
    """
    Takes an article with a structured outline and generates the full draft
    by invoking the writer-editor agent.
    """
    db = SessionLocal()
    try:
        # 1. Get the article containing the outline from the database
        article = crud.get_article(db, article_id)
        if not article:
            raise ValueError(f"Article with ID {article_id} not found.")

        # 2. Set status to show work is in progress
        crud.update_article_content(
            db, article_id, article.content, schemas.ArticleStatus.WRITING_IN_PROGRESS
        )
        
        # The content of the article is the JSON outline from Phase 1
        outline = json.loads(article.content)

        # 3. Initialize the agent's state (its starting memory)
        initial_state = GraphState(
            original_outline=outline,
            article_draft=ArticleDraft(h1=outline['h1'], sections=[]),
            current_section_index=0,
            current_section_content="",
            editor_feedback=None,
            revision_attempts=0,
        )

        # 4. Invoke the LangGraph agent to do the work
        print(f"Invoking writer-editor agent for article {article_id}...")
        final_state = writing_agent_app.invoke(initial_state)
        final_draft = final_state['article_draft']

        # 5. Format the final draft from the agent's output into clean Markdown
        final_content = f"# {final_draft.h1}\n\n"
        for section in final_draft.sections:
            final_content += f"## {section.h2}\n\n{section.content}\n\n"
        
        # 6. Save the completed draft to the database
        crud.update_article_content(
            db, article_id, final_content, schemas.ArticleStatus.DRAFT_COMPLETE
        )

        print(f"Article {article_id} draft successfully generated and saved.")
        return {"status": "SUCCESS", "article_id": article_id}

    except Exception as e:
        print(f"Article generation task failed for article {article_id}: {e}")
        # Revert status back to DRAFT on failure
        crud.update_article_content(
            db, article_id, article.content, schemas.ArticleStatus.DRAFT
        )
        raise e
    finally:
        db.close()