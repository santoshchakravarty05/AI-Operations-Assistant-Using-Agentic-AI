# AI IT Support Assistant

A local AI support assistant for a fictional organisation. It will use LangGraph and an LLM with tool calling to answer knowledge-base questions, look up existing support tickets, and create validated new tickets.

## Planned technology

- Python
- LangGraph
- Google Gemini API tool calling
- Streamlit
- Local JSON sample data

## Project structure

```text
it-support-assistant/
├── app.py                 # Streamlit entry point (added in a later step)
├── src/                   # Application modules
├── data/                  # Sample knowledge-base, ticket, and employee data
├── requirements.txt       # Python dependencies
├── .env.example           # Required environment-variable template
├── .gitignore             # Files excluded from version control
└── README.md
```

## Setup (when implementation begins)

1. Create and activate a Python virtual environment.
2. Install dependencies with `pip install -r requirements.txt`.
3. Copy `.env.example` to `.env`, then add your `GEMINI_API_KEY`. Set `GEMINI_MODEL` to a Gemini model available to that key if needed.
4. Run `streamlit run app.py`.

## Scope

The implementation will be added incrementally: sample data and schemas, local tools, the LangGraph workflow, then the Streamlit interface and documentation.

## Current workflow

The LangGraph workflow retains conversation messages and loops through this path when a tool is needed:

```text
User message → Assistant decision → Conditional route
                                      ├─ no tool → final answer
                                      └─ tool call → local tool → assistant response
```

The Streamlit interface provides a chat history, a new-conversation control, tool-result visibility, and friendly error messages.
