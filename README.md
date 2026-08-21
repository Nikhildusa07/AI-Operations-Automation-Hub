# AI Operations Automation Hub

> An AI-powered business operations platform that transforms incoming business requests into structured, actionable workflows using FastAPI, Google Gemini AI, automated decision-making, human-in-the-loop review, database persistence, notifications, and an administrative dashboard.

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.141.1-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Gemini AI](https://img.shields.io/badge/Google%20Gemini-AI-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.x-D71F00?style=for-the-badge)](https://www.sqlalchemy.org/)
[![Pydantic](https://img.shields.io/badge/Pydantic-2.x-E92063?style=for-the-badge)](https://docs.pydantic.dev/)

---

## 📌 Overview

AI Operations Automation Hub is a backend-driven business automation platform designed to process operational requests and convert them into structured workflows.

Instead of treating AI as only a chatbot, the system integrates AI into a complete business workflow:

```text
Business Request
       ↓
FastAPI
       ↓
Validation
       ↓
Database Persistence
       ↓
AI Analysis
       ↓
Decision Engine
       ↓
┌───────────────┬────────────────┐
│               │                │
▼               ▼                │
Automation   Human Review        │
│               │                │
│        Approve / Reject        │
│               │                │
└───────────────┴────────────────┘
               ↓
        Workflow Update
               ↓
        Notification
               ↓
        Activity Tracking
               ↓
       Admin Dashboard


🎯 Project Objective

The primary objective is to demonstrate how generative AI can be integrated with a production-style backend application to automate business operations while maintaining human oversight.

The system follows five core stages:

Capture business requests.
Validate and store request information.
Analyze requests using AI.
Determine the appropriate workflow.
Review and track actions when human intervention is required.
✨ Key Features
📨 1. Business Request Intake

Business requests can be submitted through the application's web interface and API.

Features include:

REST API request handling
Web-based request submission
Pydantic validation
Structured request processing
Database persistence
Request status tracking
🧠 2. Google Gemini AI Integration

The platform integrates Google Gemini through the Google GenAI SDK.

The AI service is responsible for analyzing incoming business information and providing structured analysis for downstream workflow processing.

AI responsibilities
Understand incoming requests
Analyze business information
Extract relevant information
Assist decision-making
Support automation workflows
Generate structured AI output

AI logic is isolated inside a dedicated service layer rather than being tightly coupled to API routes.

⚙️ 3. Automated Decision Making

The decision service evaluates request information and AI analysis to determine the next workflow step.

The system can route requests toward:

Automated processing
Human review
Approval
Rejection
Follow-up workflows

This allows AI to participate in an actual operational process instead of simply generating text.

👤 Human-in-the-Loop Review

AI should not blindly execute every business decision.

The system provides a review workflow for cases that require human validation.

AI Analysis
     ↓
Decision
     ↓
Needs Review?
   /       \
 No         Yes
 ↓           ↓
Action    Human Review
             ↓
       Approve / Reject
             ↓
        Continue Workflow

This provides a balance between AI automation and human control.

📊 Administrative Dashboard

The application provides an administrative dashboard for monitoring business operations.

The dashboard provides visibility into:

Business requests
Request status
Automation activity
Reviews
Operational records
Workflow activity
Reports

This creates a centralized operational interface instead of requiring administrators to inspect backend records directly.

🔐 Authentication & Sessions

The application includes authentication and session-based access.

Session management is implemented using Starlette's SessionMiddleware.

Sensitive configuration is provided through environment variables.

Production session configuration supports:

Secure cookies
SameSite protection
Session expiration
Environment-based secret configuration
🗄️ Database Persistence

SQLAlchemy 2.x is used for database interaction.

The application separates database functionality from API routing through dedicated modules:

app/database.py
app/models.py

Business workflows can therefore persist request and operational information for later processing and review.

📧 Notifications

The project includes a dedicated notification service.

Notification logic is separated from:

API routes
AI services
Decision services
Database models
Automation services

This modular structure allows the notification implementation to be extended or replaced independently.

📝 Activity & Workflow Tracking

The platform maintains operational activity records so that business workflows can be tracked.

The system can record information related to:

Requests
Decisions
Automation actions
Human reviews
Notifications
Status changes
Operational activity

This creates an auditable workflow rather than treating every AI request as an isolated interaction.

📄 Documents & Knowledge

The application also contains dedicated modules for document and knowledge-related functionality.

Relevant components include:

app/routes/documents.py
app/routes/knowledge.py
app/services/document_service.py
app/services/knowledge_service.py

These provide a foundation for business information and document-oriented automation workflows.

📅 Tasks, Meetings & Scheduling

The application contains dedicated functionality for operational coordination.

Components include:

Tasks
Meetings
Scheduler
Activity Logs

These modules allow the platform to extend beyond request processing into broader business operations management.

📈 Reports & AI Cost Tracking

The system includes reporting and AI cost-related functionality.

Relevant components include:

app/routes/reports.py
app/services/report_service.py


app/routes/ai_cost.py
app/services/ai_cost_service.py

This provides a foundation for monitoring operational reporting and AI usage-related information.

🔌 External API Integrations

The project includes an external API integration layer:

app/routes/external_api.py

This provides a structured location for connecting the application with external business systems and APIs.

🧪 Testing

The repository contains dedicated test modules for major application components.

test_ai.py
test_automation.py
test_automation_db.py
test_brevo.py
test_decision.py
test_gemini.py
test_smtp.py

Testing areas include:

AI processing
Gemini integration
Automation logic
Database-backed automation
Decision processing
Email/SMTP functionality
Notification integrations
🏗️ System Architecture

The application follows a modular layered architecture.

                  ┌─────────────────────┐
                  │    User / Admin     │
                  └──────────┬──────────┘
                             │
                             ▼
                  ┌─────────────────────┐
                  │ Web Forms / REST API│
                  └──────────┬──────────┘
                             │
                             ▼
                  ┌─────────────────────┐
                  │       FastAPI       │
                  │    Routing Layer    │
                  └──────────┬──────────┘
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
          ▼                  ▼                  ▼
   ┌────────────┐     ┌────────────┐     ┌────────────┐
   │ AI Service │     │  Decision  │     │ Automation │
   │            │     │  Service   │     │  Service   │
   └──────┬─────┘     └──────┬─────┘     └──────┬─────┘
          │                  │                  │
          └──────────────────┼──────────────────┘
                             │
                             ▼
                  ┌─────────────────────┐
                  │    SQLAlchemy ORM   │
                  └──────────┬──────────┘
                             │
                             ▼
                  ┌─────────────────────┐
                  │      Database       │
                  └──────────┬──────────┘
                             │
                             ▼
                  ┌─────────────────────┐
                  │ Notification / Logs │
                  └─────────────────────┘
📁 Project Structure
AI-Operations-Automation-Hub/
│
├── app/
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── activity_logs.py
│   │   ├── ai_cost.py
│   │   ├── auth.py
│   │   ├── automation.py
│   │   ├── customer.py
│   │   ├── dashboard.py
│   │   ├── data.py
│   │   ├── decision.py
│   │   ├── documents.py
│   │   ├── emails.py
│   │   ├── external_api.py
│   │   ├── invoices.py
│   │   ├── knowledge.py
│   │   ├── meetings.py
│   │   ├── reports.py
│   │   ├── requests.py
│   │   ├── reviews.py
│   │   ├── scheduler.py
│   │   ├── support.py
│   │   ├── tasks.py
│   │   ├── user.py
│   │   └── web_form.py
│   │
│   ├── services/
│   │   ├── agent_service.py
│   │   ├── ai_cost_service.py
│   │   ├── ai_service.py
│   │   ├── audit_service.py
│   │   ├── automation_service.py
│   │   ├── data_service.py
│   │   ├── decision_service.py
│   │   ├── document_service.py
│   │   ├── email_service.py
│   │   ├── knowledge_service.py
│   │   ├── meeting_service.py
│   │   ├── notification_service.py
│   │   ├── report_service.py
│   │   ├── scheduler_service.py
│   │   ├── support_service.py
│   │   └── task_service.py
│   │
│   ├── templates/
│   │   └── ...
│   │
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   └── main.py
│
├── docs/
│   ├── AI_Evaluation/
│   ├── API_Integrations/
│   ├── Automation_Workflows/
│   ├── Failure_Testing/
│   └── Prompt_Injection/
│
├── test_ai.py
├── test_automation.py
├── test_automation_db.py
├── test_brevo.py
├── test_decision.py
├── test_gemini.py
├── test_smtp.py
│
├── .env.example
├── .gitignore
├── render.yaml
├── requirements.txt
└── README.md
🛠️ Technology Stack
Technology	Purpose
Python 3.11+	Core programming language
FastAPI	Backend API and web application
Uvicorn	ASGI server
Pydantic	Request/data validation
SQLAlchemy	ORM and database interaction
Jinja2	Server-side HTML templates
Starlette	Session middleware
Google Gemini	Generative AI
Google GenAI SDK	Gemini API integration
python-dotenv	Environment configuration
HTTPX	HTTP client/testing
SMTP / Brevo	Notification/email functionality
🚀 Getting Started
1. Clone the Repository
git clone https://github.com/Nikhildusa07/AI-Operations-Automation-Hub.git
cd AI-Operations-Automation-Hub
2. Create a Virtual Environment
Windows
python -m venv venv
venv\Scripts\activate
macOS / Linux
python3 -m venv venv
source venv/bin/activate
3. Install Dependencies
pip install -r requirements.txt
🔐 Environment Configuration

Create a .env file in the project root.

Example:

SECRET_KEY=your-secret-key


GEMINI_API_KEY=your-gemini-api-key


GOOGLE_API_KEY=your-google-api-key


SMTP_HOST=your-smtp-host
SMTP_PORT=587
SMTP_USERNAME=your-email
SMTP_PASSWORD=your-password

Depending on the enabled integrations, additional environment variables may be required.

Important: Never commit .env files, API keys, passwords, or other secrets to GitHub.

The repository includes:

.env.example

for environment configuration reference.

▶️ Run Locally

Start the FastAPI application:

uvicorn app.main:app --reload

Open:

http://127.0.0.1:8000
❤️ Health Check

The application exposes a health endpoint:

GET /health

Example response:

{
  "status": "healthy",
  "service": "AI Operations Automation Hub",
  "version": "1.0.0"
}

This endpoint can also be used by deployment platforms for service health monitoring.

📚 API Documentation

FastAPI automatically generates interactive documentation.

Swagger UI
http://127.0.0.1:8000/docs
ReDoc
http://127.0.0.1:8000/redoc
🧪 Running Tests

Individual tests can be executed using:

python test_ai.py
python test_automation.py
python test_automation_db.py
python test_brevo.py
python test_decision.py
python test_gemini.py
python test_smtp.py
🔄 End-to-End Business Workflow

A typical request moves through the following process:

                Business Request
                       │
                       ▼
                Request Intake
                       │
                       ▼
                  Validation
                       │
                       ▼
              Database Persistence
                       │
                       ▼
                  AI Analysis
                       │
                       ▼
                Decision Engine
                       │
             ┌─────────┴─────────┐
             │                   │
             ▼                   ▼
       Automated Action      Human Review
             │                   │
             │            ┌──────┴──────┐
             │            ▼             ▼
             │        Approved       Rejected
             │            │             │
             └────────────┴─────────────┘
                          │
                          ▼
                  Workflow Update
                          │
                          ▼
                     Notification
                          │
                          ▼
                    Activity Log
                          │
                          ▼
                   Admin Dashboard
🎯 Example Business Scenario

Imagine a company receives a large number of operational requests.

Traditional process
Request
   ↓
Employee reads request
   ↓
Employee decides action
   ↓
Employee performs action
   ↓
Employee sends notification
   ↓
Employee updates records
Automated process
Request
   ↓
FastAPI
   ↓
Validation
   ↓
Gemini AI
   ↓
Decision Engine
   ↓
Automation / Human Review
   ↓
Notification
   ↓
Database
   ↓
Admin Dashboard

The system therefore acts as an AI-assisted business operations layer.

🔒 Security Considerations

For production deployments:

Never commit .env files.
Never expose API keys in frontend code.
Use HTTPS.
Use secure session cookies.
Configure a production database.
Implement proper authentication and authorization.
Validate external input.
Apply rate limiting to public endpoints.
Store secrets using deployment-platform environment variables.
Monitor application logs.
Keep human approval for sensitive automated actions.
Avoid allowing untrusted AI output to directly perform high-impact operations without validation.
☁️ Deployment

The repository includes:

render.yaml

for deployment configuration.

The application can be deployed as a FastAPI web service using a production ASGI server.

A typical production command is:

uvicorn app.main:app --host 0.0.0.0 --port $PORT

Production environment variables should be configured through the deployment platform rather than committed to the repository.

📈 Future Enhancements

Potential improvements include:

Authentication
Role-based access control
Multiple administrator roles
Permission management
OAuth / SSO
AI
Specialized AI agents
Tool calling
Structured function execution
Confidence scoring
More advanced AI workflows
Workflow Automation
Configurable workflows
Multi-step approvals
SLA monitoring
Automatic escalation
Conditional workflow branches
Analytics
Request volume
Automation success rate
Average processing time
Human review rate
AI usage and cost analytics
Infrastructure
PostgreSQL
Redis
Background workers
Docker
CI/CD
Cloud monitoring
Application observability
Integrations
Slack
Microsoft Teams
Gmail
CRM systems
ERP systems
Helpdesk platforms
Webhooks
External REST APIs
💡 What This Project Demonstrates

This project demonstrates practical experience with:

Python backend development
FastAPI
REST APIs
Pydantic validation
SQLAlchemy ORM
Database-driven workflows
Generative AI
Google Gemini integration
AI-assisted decision making
Business process automation
Human-in-the-loop architecture
Authentication and sessions
Server-side templating
Notification systems
Activity tracking
Reporting
External API integration
Automated testing
Environment-based configuration
Production-oriented deployment
📌 Project Status

Status: Completed Core Implementation — Deployment Ready

The current implementation includes:

FastAPI backend
REST API
Web-based request intake
Pydantic validation
SQLAlchemy database layer
Google Gemini integration
AI service layer
Decision service
Automation service
Human review workflow
Authentication
Session management
Customer portal
Administrative dashboard
Notification functionality
Activity logging
Document functionality
Knowledge functionality
Task management
Meeting functionality
Scheduling
Invoice functionality
Reporting
AI cost tracking
External API integration
Automated component tests
Render deployment configuration
👨‍💻 Author
Nikhil

AI & ML Engineer | Python Backend Developer | AI Automation Developer

Focused on building practical systems combining:

Python
+
Backend Engineering
+
Artificial Intelligence
+
Automation
+
Full-Stack Development
🌐 Repository

GitHub:

https://github.com/Nikhildusa07/AI-Operations-Automation-Hub

📄 License

This project is developed for educational, internship, portfolio, and demonstration purposes.

🚀 Final Takeaway

AI Operations Automation Hub demonstrates how generative AI can be integrated into a real backend application to transform business requests into structured, traceable operational workflows.

The platform combines:

Business Requests
        ↓
FastAPI
        ↓
Validation
        ↓
Gemini AI
        ↓
Decision Engine
        ↓
Automation
        +
Human Review
        ↓
Notifications
        ↓
Database & Activity Tracking
        ↓
Administrative Dashboard

The core objective is simple:

Turn repetitive business operations into intelligent, traceable, and human-supervised automated workflows.



### Important changes I made


- Changed the project name everywhere to **AI Operations Automation Hub**.
- Changed the GitHub repository from the old `AI-Business-Automation` to your actual repository:
  `AI-Operations-Automation-Hub`.
- Updated the project structure to match the files you actually showed in `git status`.
- Added your `docs/` structure.
- Added `render.yaml`.
- Added the modules you actually have: invoices, reports, AI cost, meetings, scheduler, knowledge, external API, etc.
- Removed claims that weren't necessary or that could be misleading.
- Added `/health`, which is useful for deployment.
- Added a deployment section.
- Made the README more professional for an **internship/project evaluation** rather than excessively long.
- Changed status to **Completed Core Implementation — Deployment Ready**, which fits where you are now.


### Now update GitHub


After replacing the README:


```powershell
git add README.md
git commit -m "Update project README for deployment"
git push
