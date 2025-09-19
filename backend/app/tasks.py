# # tasks.py

# In backend/app/tasks.py

import os
import json
from typing import List, Optional
# --- Imports for parallel processing are no longer needed for this approach ---
# from concurrent.futures import ThreadPoolExecutor, as_completed

from .celery_config import celery_app
from .services import serp_service, scraper_service
from . import crud, schemas
from .database import SessionLocal

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
from langchain.output_parsers.fix import OutputFixingParser
from tenacity import Retrying, stop_after_attempt, wait_exponential, RetryError
from .models import TopicClusterList, SeoOutline # Assuming models are here

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

@celery_app.task(bind=True)
def generate_outline_task(self, project_id: int, keyword: str, manual_keywords: Optional[List[str]] = None):
    db = SessionLocal()
    try:
        crud.update_project_status(db, project_id=project_id, status=schemas.ProjectStatus.IN_PROGRESS)

        print("Fetching SERP data...")
        try:
            retryer = Retrying(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
            serp_data = retryer(serp_service.get_serp_results, keyword)
        except RetryError as e:
            print(f"Task failed: Failed to fetch SERP data after multiple retries. Last error: {e}")
            raise ValueError("Failed to fetch SERP data.")

        if "error" in serp_data or "organic" not in serp_data:
            raise ValueError("Failed to fetch SERP data.")

        urls = [result['link'] for result in serp_data.get('organic', [])[:10]]
        
        # --- SEQUENTIAL (NON-PARALLEL) SCRAPING LOGIC ---
        scraped_headings = []
        print("Starting sequential scrape of URLs...")
        for url in urls:
            # The intelligent hybrid logic is still inside this function call
            # It will attempt ScrapingAnt first, then Bright Data on failure.
            headings = scraper_service.scrape_url_for_headings(url)
            if headings:
                scraped_headings.extend(headings)
        
        scraped_content_for_prompt = "\n".join(scraped_headings)
        print(f"Scraped {len(scraped_headings)} headings from top {len(urls)} URLs.")

        # --- AI Step 1: Topic Grouper ---
        print(f"Grouping topics with {DEV_OPENAI_MODEL_GROUPER}...")
        grouper_parser = PydanticOutputParser(pydantic_object=TopicClusterList)
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
            "manual_keywords": ", ".join(manual_keywords) if manual_keywords else "None"
        })

        # --- AI Step 2: Outline Architect ---
        print(f"Architecting outline with {DEV_ANTHROPIC_MODEL_ARCHITECT}...")
        architect_parser = PydanticOutputParser(pydantic_object=SeoOutline)
        output_fixing_parser = OutputFixingParser.from_llm(parser=architect_parser, llm=ChatOpenAI(model=DEV_OPENAI_MODEL_GROUPER))
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
        
        llm_refiner = ChatAnthropic(model=DEV_ANTHROPIC_MODEL_REFINER, temperature=0, api_key=ANTHROPIC_API_KEY)
        chain_refiner = refiner_prompt | llm_refiner | refiner_parser
        final_outline = chain_refiner.invoke({
            "format_instructions": refiner_parser.get_format_instructions(),
            "keyword": keyword,
            "draft_outline_json": draft_outline.model_dump_json(),
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





# import os
# import json
# from typing import List, Optional
# # --- Import the necessary tools for parallel processing ---
# from concurrent.futures import ThreadPoolExecutor, as_completed

# from .celery_config import celery_app
# from .services import serp_service, scraper_service
# from . import crud, schemas, models
# from .database import SessionLocal
# from .agents.writer_editor_agent import app as writing_agent_app, GraphState, ArticleDraft

# from tenacity import Retrying, stop_after_attempt, wait_exponential, RetryError

# from .config import (
#     DEV_OPENAI_MODEL_GROUPER,
#     DEV_ANTHROPIC_MODEL_ARCHITECT,
#     DEV_ANTHROPIC_MODEL_REFINER
# )

# from .prompts import (
#     TOPIC_GROUPER_SYSTEM_PROMPT,
#     TOPIC_GROUPER_USER_PROMPT,
#     OUTLINE_ARCHITECT_SYSTEM_PROMPT,
#     OUTLINE_ARCHITECT_USER_PROMPT,
#     OUTLINE_REFINER_SYSTEM_PROMPT
# )

# from langchain_openai import ChatOpenAI
# from langchain_anthropic import ChatAnthropic
# from langchain.prompts import ChatPromptTemplate
# from langchain_core.output_parsers import PydanticOutputParser
# from langchain.output_parsers.fix import OutputFixingParser

# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# @celery_app.task(bind=True)
# def generate_outline_task(self, project_id: int, keyword: str, manual_keywords: Optional[List[str]] = None):
#     db = SessionLocal()
#     try:
#         crud.update_project_status(db, project_id=project_id, status=schemas.ProjectStatus.IN_PROGRESS)

#         print("Fetching SERP data...")
#         serp_data = {}
#         try:
#             retryer = Retrying(
#                 stop=stop_after_attempt(3),
#                 wait=wait_exponential(multiplier=1, min=2, max=10)
#             )
#             serp_data = retryer(serp_service.get_serp_results, keyword)
#         except RetryError as e:
#             print(f"Task failed: Failed to fetch SERP data after multiple retries. Last error: {e}")
#             raise ValueError("Failed to fetch SERP data.") from e

#         if "error" in serp_data or "organic" not in serp_data:
#             raise ValueError("Failed to fetch SERP data or SERP data is invalid.")

#         urls = [result['link'] for result in serp_data.get('organic', [])[:10]]
        
#         # --- PARALLEL SCRAPING LOGIC ---
#         scraped_headings = []
#         # We create a pool of 5 "worker" threads to scrape simultaneously.
#         with ThreadPoolExecutor(max_workers=5) as executor:
#             # Create a future object for each URL to be scraped.
#             future_to_url = {executor.submit(scraper_service.scrape_url_for_headings, url): url for url in urls}
            
#             # Process the results as they are completed.
#             for future in as_completed(future_to_url):
#                 url = future_to_url[future]
#                 try:
#                     # Get the result from the completed future.
#                     headings = future.result()
#                     if headings:
#                         scraped_headings.extend(headings)
#                 except Exception as exc:
#                     print(f'{url} generated an exception during scraping: {exc}')
#         # --- END OF PARALLEL SCRAPING LOGIC ---

#         scraped_content_for_prompt = "\n".join(scraped_headings)
#         print(f"Scraped {len(scraped_headings)} headings from top {len(urls)} URLs.")

#         # --- AI Step 1: Topic Grouper ---
#         print(f"Grouping topics with {DEV_OPENAI_MODEL_GROUPER}...")
#         grouper_parser = PydanticOutputParser(pydantic_object=models.TopicClusterList)
#         grouper_prompt = ChatPromptTemplate.from_messages(
#             [
#                 ("system", TOPIC_GROUPER_SYSTEM_PROMPT),
#                 ("user", TOPIC_GROUPER_USER_PROMPT),
#             ]
#         )
#         llm_grouper = ChatOpenAI(model=DEV_OPENAI_MODEL_GROUPER, temperature=0, api_key=OPENAI_API_KEY)
#         chain_grouper = grouper_prompt | llm_grouper | grouper_parser
        
#         topic_clusters = chain_grouper.invoke({
#             "format_instructions": grouper_parser.get_format_instructions(),
#             "scraped_content": scraped_content_for_prompt,
#             "manual_keywords": ", ".join(manual_keywords) if manual_keywords else "None"
#         })

#         # --- AI Step 2: Outline Architect ---
#         print(f"Architecting outline with {DEV_ANTHROPIC_MODEL_ARCHITECT}...")
#         architect_parser = PydanticOutputParser(pydantic_object=models.SeoOutline)

#         output_fixing_parser = OutputFixingParser.from_llm(
#             parser=architect_parser, llm=ChatOpenAI(model=DEV_OPENAI_MODEL_GROUPER)
#         )

#         architect_prompt = ChatPromptTemplate.from_messages(
#             [
#                 ("system", OUTLINE_ARCHITECT_SYSTEM_PROMPT),
#                 ("user", OUTLINE_ARCHITECT_USER_PROMPT),
#             ]
#         )
        
#         if ANTHROPIC_API_KEY:
#             llm_architect = ChatAnthropic(model=DEV_ANTHROPIC_MODEL_ARCHITECT, temperature=0, api_key=ANTHROPIC_API_KEY)
#         else:
#             llm_architect = ChatOpenAI(model=DEV_OPENAI_MODEL_GROUPER, temperature=0, api_key=OPENAI_API_KEY)

#         chain_architect = architect_prompt | llm_architect | output_fixing_parser
        
#         draft_outline = chain_architect.invoke({
#             "format_instructions": architect_parser.get_format_instructions(),
#             "keyword": keyword,
#             "topic_clusters_json": topic_clusters.model_dump_json()
#         })

#         # --- AI Step 3: Outline Refiner ---
#         print(f"Refining outline with {DEV_ANTHROPIC_MODEL_REFINER}...")
        
#         refiner_parser = architect_parser 
        
#         refiner_prompt = ChatPromptTemplate.from_messages(
#             [
#                 ("system", OUTLINE_REFINER_SYSTEM_PROMPT),
#                 ("user", """
#                  <output_instructions>
#                  {format_instructions}
#                  </output_instructions>

#                  **Primary Keyword:** "{keyword}"

#                  <draft_outline>
#                  {draft_outline_json}
#                  </draft_outline>
#                  """),
#             ]
#         )
        
#         llm_refiner = ChatAnthropic(
#             model=DEV_ANTHROPIC_MODEL_REFINER, temperature=0, api_key=ANTHROPIC_API_KEY
#         )
        
#         chain_refiner = refiner_prompt | llm_refiner | refiner_parser

#         final_outline = chain_refiner.invoke(
#             {
#                 "format_instructions": refiner_parser.get_format_instructions(),
#                 "keyword": keyword,
#                 "draft_outline_json": draft_outline.model_dump_json(),
#             }
#         )

#         # --- Save the final result ---
#         article_title = final_outline.h1
#         article_content = final_outline.model_dump_json(indent=2)
        
#         crud.create_article_for_project(db, title=article_title, content=article_content, project_id=project_id)
#         crud.update_project_status(db, project_id=project_id, status=schemas.ProjectStatus.COMPLETED)
        
#         print("Task succeeded. Outline saved to database.")
#         return {"status": "SUCCESS", "outline_h1": article_title}

#     except Exception as e:
#         print(f"Task failed: {e}")
#         crud.update_project_status(db, project_id=project_id, status=schemas.ProjectStatus.FAILED)
#         raise e
#     finally:
#         db.close()




