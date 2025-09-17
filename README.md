# SEO-AI-AGENT - Backend Services

This repository contains the backend services for **SEO-AI-AGENT**, a scalable, industry-level platform that automates a proprietary SEO content workflow. The system operates as an AI Co-pilot, a specialized "SEO Automation Agent," that transforms a single keyword into a fully researched, strategically planned, and written content package.

---

## 🚀 Project Status

**Current Phase:** Phase 2: Entity-Driven Intelligence Layer - ✅ **Completed**

The system can now perform deep conceptual analysis on competitor content to produce highly strategic, entity-aware outlines. We are currently beginning development on Phase 3.

---

## 🛠️ Technology Stack

| Category                  | Selected Tool/Library                         |
| ------------------------- | --------------------------------------------- |
| **AI Orchestration** | LangChain, LangGraph                          |
| **LLM Providers** | OpenAI, Anthropic                             |
| **Local NLP** | spaCy (`en_core_web_lg`)                      |
| **Backend Framework** | FastAPI                                       |
| **Asynchronous Tasks** | Celery & Redis                                |
| **Database (Relational)** | PostgreSQL                                    |
| **Data Acquisition** | Serper.dev, ScrapingAnt                       |
| **Development Env** | Python 3.11 with Poetry                       |
| **Deployment** | Docker, GCP (Cloud Run, Cloud SQL)            |

---

## 🗺️ Finalized Roadmap

* **Phase 1: Strategic Outlining Engine** - ✅ **Completed**
    * Generates a structured JSON outline from a keyword based on competitor headings.

* **Phase 2: Entity-Driven Intelligence Layer** - ✅ **Completed**
    * Upgrades analysis from headings to full-text, using spaCy for local entity extraction to create a "conceptual fingerprint" that enriches the AI's strategic input.

* **Phase 3: Content Co-pilot Engine** - ⏳ **In Progress**
    * Build the autonomous "Writer-Editor" LangGraph agent to transform outlines into full article drafts.

* **Phase 4: Optimization & Enrichment Services** - 📋 **Planned**
    * Build advanced features like an internal linking architect (RAG) and qualitative content scoring.

* **Phase 5: Final Assets & Authentication** - 📋 **Planned**
    * Generate final assets (meta tags, social posts) and implement JWT-based user authentication.

* **Phase 6: MLOps & Production Deployment** - 📋 **Planned**
    * Full containerization and deployment to a production environment on GCP.

---

## ⚙️ Local Development Setup

Follow these steps to get the backend services running locally.

### 1. Prerequisites
* **Python 3.11**
* **Poetry** for dependency management (`pip install poetry`)
* **Docker Desktop** running on your machine (for Redis).

### 2. Clone the Repository
```bash
git clone <your-repo-url>
cd seo-ai-agent/backend
3. Environment Setup
Create a .env file in the backend directory by copying the example file.
```
```bash

cp .env.example .env
```
### Now, open the .env file and add your secret API keys:
```
DATABASE_URL="postgresql://user:password@localhost/seo_agent_db"
OPENAI_API_KEY="sk-..."
ANTHROPIC_API_KEY="sk-..."
SERPER_API_KEY="..."
SCRAPINGANT_API_KEY="..."
4. Install Dependencies & Models
Poetry will create a virtual environment and install all necessary Python packages.
```

```bash
# Install dependencies
poetry install
```
## Download the required spaCy model
```bash
poetry run python -m spacy download en_core_web_lg
```

5. Run Services
- You will need three separate terminal windows.

>Terminal 1: Run Redis

```bash

docker run -d -p 6379:6379 redis
Terminal 2: Run the Celery Worker
```

```bash

# Navigate to the backend directory
cd /path/to/seo-ai-agent/backend

# Start the worker
poetry run celery -A app.celery_config.celery_app worker --loglevel=info
Terminal 3: Run the FastAPI Server

```
```bash

# Navigate to the backend directory
cd /path/to/seo-ai-agent/backend

# Start the server
poetry run uvicorn app.main:app --reload
```
> The API will now be available at http://127.0.0.1:8000.