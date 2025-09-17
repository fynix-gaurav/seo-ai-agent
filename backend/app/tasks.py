# In fynix-gaurav/seo-ai-agent/seo-ai-agent-main/backend/app/tasks.py

import os
import json
from typing import List, Optional
from .celery_config import celery_app
from .services import serp_service, scraper_service, nlp_service
from . import crud, schemas, models
from .database import SessionLocal
from .agents.writer_editor_agent import app as writing_agent_app, GraphState, ArticleDraft

from .config import (
    DEV_OPENAI_MODEL_GROUPER,
    DEV_ANTHROPIC_MODEL_ARCHITECT,
    DEV_ANTHROPIC_MODEL_REFINER
)
from .prompts import (
    TOPIC_GROUPER_SYSTEM_PROMPT,
    TOPIC_GROUPER_USER_PROMPT,
    OUTLINE_ARCHITECT_SYSTEM_PROMPT,
    OUTLINE_ARCHITECT_USER_PROMPT,
    OUTLINE_REFINER_SYSTEM_PROMPT,
    OUTLINE_REFINER_USER_PROMPT
)

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain.output_parsers import OutputFixingParser


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

@celery_app.task(bind=True)
def generate_outline_task(self, project_id: int, keyword: str, location: Optional[str] = None, manual_keywords: Optional[List[str]] = None):
    db = SessionLocal()
    try:
        crud.update_project_status(db, project_id=project_id, status=schemas.ProjectStatus.IN_PROGRESS)

        print("Fetching SERP data...")
        serp_data = serp_service.get_serp_results(keyword, location=location)
        if "error" in serp_data or "organic" not in serp_data:
            raise ValueError("Failed to fetch SERP data.")

        urls = [result['link'] for result in serp_data.get('organic', [])[:10]]
        
        # --- PHASE 2: DUAL SCRAPING FOR FULL TEXT AND HEADINGS ---
        all_scraped_text = []
        all_scraped_headings = []
        for url in urls:
            # Scrape full text for entity analysis
            full_text = scraper_service.scrape_and_clean_url(url)
            if full_text:
                all_scraped_text.append(full_text)
            
            # Scrape headings for structural analysis
            headings = scraper_service.scrape_url_for_headings(url)
            if headings:
                all_scraped_headings.extend(headings)

        # --- PHASE 2: NLP ENTITY EXTRACTION ---
        aggregated_text = "\n".join(all_scraped_text)
        extracted_entities = nlp_service.extract_entities_from_text(aggregated_text)
    
        crud.update_project_entities(db, project_id=project_id, entities=extracted_entities)

        scraped_content_for_prompt = "\n".join(all_scraped_headings)
        print(f"Scraped {len(all_scraped_headings)} headings from top {len(urls)} URLs.")

        # --- AI Step 1: Topic Grouper (Enriched with Entities) ---
        print(f"Grouping topics with {DEV_OPENAI_MODEL_GROUPER}...")
        grouper_parser = PydanticOutputParser(pydantic_object=models.TopicClusterList)
        grouper_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", TOPIC_GROUPER_SYSTEM_PROMPT),
                ("user", TOPIC_GROUPER_USER_PROMPT),
            ]
        )
        llm_grouper = ChatOpenAI(model=DEV_OPENAI_MODEL_GROUPER, temperature=0, api_key=OPENAI_API_KEY)
        chain_grouper = grouper_prompt | llm_grouper | grouper_parser
        
        topic_clusters = chain_grouper.invoke({
            "format_instructions": grouper_parser.get_format_instructions(),
            "scraped_content": scraped_content_for_prompt,
            "manual_keywords": ", ".join(manual_keywords) if manual_keywords else "None",
            "extracted_entities": ", ".join(extracted_entities)
        })

        # --- AI Step 2: Outline Architect ---
        print(f"Architecting outline with {DEV_ANTHROPIC_MODEL_ARCHITECT}...")
        architect_parser = PydanticOutputParser(pydantic_object=models.SeoOutline)
        
        output_fixing_parser = OutputFixingParser.from_llm(
            parser=architect_parser, llm=ChatOpenAI(model=DEV_OPENAI_MODEL_GROUPER)
        )
        
        architect_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", OUTLINE_ARCHITECT_SYSTEM_PROMPT),
                ("user", OUTLINE_ARCHITECT_USER_PROMPT),
            ]
        )
        
        if ANTHROPIC_API_KEY:
            llm_architect = ChatAnthropic(model=DEV_ANTHROPIC_MODEL_ARCHITECT, temperature=0, api_key=ANTHROPIC_API_KEY)
        else:
            llm_architect = ChatOpenAI(model=DEV_OPENAI_MODEL_GROUPER, temperature=0, api_key=OPENAI_API_KEY)

        chain_architect = architect_prompt | llm_architect | output_fixing_parser
        
        draft_outline = chain_architect.invoke({
            "format_instructions": architect_parser.get_format_instructions(),
            "keyword": keyword,
            "topic_clusters_json": topic_clusters.model_dump_json()
        })

        # --- AI Step 3: Outline Refiner ---
        print(f"Refining outline with {DEV_ANTHROPIC_MODEL_REFINER}...")
        refiner_parser = architect_parser 
        
        refiner_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", OUTLINE_REFINER_SYSTEM_PROMPT),
                ("user", OUTLINE_REFINER_USER_PROMPT),
            ]
        )
        
        llm_refiner = ChatAnthropic(
            model=DEV_ANTHROPIC_MODEL_REFINER, temperature=0, api_key=ANTHROPIC_API_KEY
        )
        
        chain_refiner = refiner_prompt | llm_refiner | refiner_parser

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