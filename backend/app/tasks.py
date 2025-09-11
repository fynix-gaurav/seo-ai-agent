import os
import json
from typing import List, Optional
from .celery_config import celery_app
from .services import serp_service, scraper_service
from . import crud, schemas, models
from .database import SessionLocal

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

        urls = [result['link'] for result in serp_data['organic'][:5]]
        scraped_content = ""
        for url in urls:
            print(f"Scraping {url}...")
            content = scraper_service.scrape_url_content(url)
            if content:
                scraped_content += f"--- CONTENT FROM {url} ---\n{content}\n\n"

        # --- AI Step 1: Topic Grouper (GPT-3.5-Turbo) ---
        print("Grouping topics with GPT-3.5-Turbo...")
        grouper_parser = PydanticOutputParser(pydantic_object=models.TopicClusterList)
        grouper_prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a data processing and topic modeling AI. Your task is to process raw text and keywords, and group them into clean, semantically related topic clusters. You must format your output as a JSON object that strictly adheres to the provided schema."),
            ("user", """
             <output_instructions>
             {format_instructions}
             </output_instructions>
             
             <competitor_content>
             {scraped_content}
             </competitor_content>
             
             <manual_keywords>
             {manual_keywords}
             </manual_keywords>
             """)
        ])
        # --- MODEL UPDATED TO THE MOST COST-EFFECTIVE OPTION ---
        llm_grouper = ChatOpenAI(model="gpt-3.5-turbo", temperature=0, api_key=OPENAI_API_KEY)
        chain_grouper = grouper_prompt | llm_grouper | grouper_parser
        
        topic_clusters = chain_grouper.invoke({
            "format_instructions": grouper_parser.get_format_instructions(),
            "scraped_content": scraped_content,
            "manual_keywords": ", ".join(manual_keywords) if manual_keywords else "None"
        })

        # --- AI Step 2: Outline Architect (Claude 3 Haiku) ---
        print("Architecting outline with Claude 3 Haiku...")
        architect_parser = PydanticOutputParser(pydantic_object=models.SeoOutline)
        architect_prompt = ChatPromptTemplate.from_messages([
             ("system", "Act as an expert SEO Content Strategist. Your task is to take topic clusters and architect them into a final, logical content outline for a B2B audience. Your sole output is the hierarchical structure of headings. You MUST format your output as a JSON object that strictly adheres to the provided schema. Your entire response must be ONLY the JSON object, starting with `{{` and ending with `}}`. Do not include any other text, explanations, or conversational filler."),
             ("user", """
              <output_instructions>
              {format_instructions}
              </output_instructions>
              
              **Primary Keyword:** "{keyword}"

              <topic_clusters>
              {topic_clusters_json}
              </topic_clusters>
              """)
        ])
        
        
        if ANTHROPIC_API_KEY:
            llm_architect = ChatAnthropic(model="claude-3-haiku-20240307", temperature=0, api_key=ANTHROPIC_API_KEY)
        else: # Fallback to OpenAI's cheapest
            llm_architect = ChatOpenAI(model="gpt-3.5-turbo", temperature=0, api_key=OPENAI_API_KEY)

        chain_architect = architect_prompt | llm_architect | architect_parser
        
        final_outline = chain_architect.invoke({
            "format_instructions": architect_parser.get_format_instructions(),
            "keyword": keyword,
            "topic_clusters_json": topic_clusters.model_dump_json()
        })

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