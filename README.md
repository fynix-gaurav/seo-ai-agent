# SEO-AI-AGENT - Backend Services

This repository contains the backend services for **SEO-AOI-AGENT**, a scalable, industry-level platform that automates a proprietary SEO content workflow. The system operates as an AI Co-pilot, a specialized "SEO Automation Agent," that transforms a single keyword into a fully researched, strategically differentiated, and written content package.

---

## 🚀 Project Vision

Our primary goal is to build a robust, scalable, and maintainable platform that serves as a co-pilot for content strategists. The system is designed with an "asynchronous first" architecture to handle complex, long-running AI tasks while providing a responsive user experience.

### Core Features (Roadmap)
* **Phase 1: Strategy & Outlining Engine:** Autonomous generation of data-driven, structured content outlines from a single keyword.
* **Phase 2: Content Co-pilot Engine:** An agentic "Writer-Editor" workflow that transforms outlines into high-quality, full-length article drafts.
* **Phase 3: Optimization & Enrichment:** Advanced services like an Internal Linking Architect (RAG) and qualitative content scoring.
* **Phase 4: Final Assets & Security:** Generation of meta-descriptions, social posts, and implementation of JWT-based user authentication.
* **Phase 5: MLOps & Deployment:** Full containerization and deployment to a production environment on GCP.

---

## 🛠️ Technology Stack

| Category                  | Selected Tool/Library                         |
| ------------------------- | --------------------------------------------- |
| **AI Orchestration** | LangChain, LangGraph                          |
| **LLM Providers** | OpenAI, Anthropic                             |
| **Backend Framework** | FastAPI                                       |
| **Asynchronous Tasks** | Celery & Redis                                |
| **Database (Relational)** | PostgreSQL                                    |
| **Database (Vector)** | Chroma DB                                     |
| **Development Env** | Python 3.11 with Poetry                       |
| **Deployment** | Docker, GCP (Cloud Run, Cloud SQL)            |


---

## ⚙️ Local Development Setup

Follow these steps to get the backend services running locally.

### 1. Prerequisites
* **Python 3.11**
* **Poetry** for dependency management (`pip install poetry`)
* **Docker Desktop** running on your machine.

### 2. Clone the Repository
```bash
git clone <your-repo-url>
cd seo-agent/backend