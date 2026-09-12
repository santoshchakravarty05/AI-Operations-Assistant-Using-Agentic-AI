"""LLM-callable tools for the local IT support data sources."""

from __future__ import annotations

from datetime import UTC, datetime
import re
from typing import Any

from langchain_core.tools import tool

from src.data_store import DataStoreError, load_records, save_records


ACTIVE_TICKET_STATUSES = {"Open", "In Progress"}
VALID_CATEGORIES = {"Account", "Hardware", "Network", "Software", "VPN"}
VALID_PRIORITIES = {"Low", "Medium", "High"}


def _failure(code: str, message: str) -> dict[str, Any]:
    return {"success": False, "error": {"code": code, "message": message}}


def _normalise(text: str) -> str:
    return " ".join(text.casefold().split())


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.casefold()))


def _employee(employee_id: str) -> dict[str, Any] | None:
    normalized_id = employee_id.strip().upper()
    return next(
        (
            employee
            for employee in load_records("employees.json")
            if employee.get("employee_id", "").upper() == normalized_id
        ),
        None,
    )


def _next_ticket_id(tickets: list[dict[str, Any]]) -> str:
    numbers = [
        int(match.group(1))
        for ticket in tickets
        if (match := re.fullmatch(r"INC-(\d+)", str(ticket.get("ticket_id", ""))))
    ]
    return f"INC-{max(numbers, default=1000) + 1}"


@tool
def search_knowledge_base(query: str) -> dict[str, Any]:
    """Find relevant local IT knowledge-base articles for a user's support question."""
    if not isinstance(query, str) or len(query.strip()) < 3:
        return _failure("invalid_query", "Please provide a support question of at least 3 characters.")

    try:
        query_tokens = _tokens(query)
        matches: list[tuple[int, dict[str, Any]]] = []
        for article in load_records("knowledge_base.json"):
            searchable_text = " ".join(
                [
                    article.get("title", ""),
                    " ".join(article.get("keywords", [])),
                    article.get("content", ""),
                ]
            )
            score = len(query_tokens & _tokens(searchable_text))
            if score:
                matches.append((score, article))
        matches.sort(key=lambda item: item[0], reverse=True)
    except DataStoreError as error:
        return _failure("data_unavailable", str(error))

    articles = [
        {
            "article_id": article["article_id"],
            "title": article["title"],
            "content": article["content"],
        }
        for _, article in matches[:3]
    ]
    if not articles:
        return _failure("no_match", "No matching knowledge-base article was found.")
    return {"success": True, "articles": articles}


@tool
def lookup_tickets(employee_id: str, ticket_id: str | None = None) -> dict[str, Any]:
    """Look up a known employee's support tickets, optionally by an exact ticket ID."""
    if not isinstance(employee_id, str) or not employee_id.strip():
        return _failure("missing_employee_id", "Please provide an employee ID, for example EMP1024.")

    try:
        employee = _employee(employee_id)
        if not employee:
            return _failure("employee_not_found", "No employee was found for that employee ID.")
        tickets = [
            ticket
            for ticket in load_records("tickets.json")
            if ticket.get("employee_id", "").upper() == employee["employee_id"].upper()
        ]
    except DataStoreError as error:
        return _failure("data_unavailable", str(error))

    if ticket_id:
        tickets = [
            ticket
            for ticket in tickets
            if ticket.get("ticket_id", "").upper() == ticket_id.strip().upper()
        ]
    if not tickets:
        return _failure("ticket_not_found", "No matching ticket was found for this employee.")

    return {
        "success": True,
        "employee": {"employee_id": employee["employee_id"], "name": employee["name"]},
        "tickets": tickets,
    }


@tool
def create_ticket(
    employee_id: str,
    title: str,
    description: str,
    category: str,
    priority: str = "Medium",
) -> dict[str, Any]:
    """Create a validated IT ticket after required details are available."""
    if not isinstance(employee_id, str) or not employee_id.strip():
        return _failure("missing_employee_id", "An employee ID is required to create a ticket.")
    if not isinstance(title, str) or len(title.strip()) < 5:
        return _failure("invalid_title", "Provide a ticket title with at least 5 characters.")
    if not isinstance(description, str) or len(description.strip()) < 10:
        return _failure("invalid_description", "Provide a description with at least 10 characters.")

    category = category.strip().title() if isinstance(category, str) else ""
    priority = priority.strip().title() if isinstance(priority, str) else ""
    if category not in VALID_CATEGORIES:
        return _failure("invalid_category", f"Category must be one of: {', '.join(sorted(VALID_CATEGORIES))}.")
    if priority not in VALID_PRIORITIES:
        return _failure("invalid_priority", f"Priority must be one of: {', '.join(sorted(VALID_PRIORITIES))}.")

    try:
        employee = _employee(employee_id)
        if not employee:
            return _failure("employee_not_found", "No employee was found for that employee ID.")
        tickets = load_records("tickets.json")

        normalized_title = _normalise(title)
        duplicate = next(
            (
                ticket
                for ticket in tickets
                if ticket.get("employee_id", "").upper() == employee["employee_id"].upper()
                and ticket.get("status") in ACTIVE_TICKET_STATUSES
                and _normalise(str(ticket.get("title", ""))) == normalized_title
            ),
            None,
        )
        if duplicate:
            return _failure(
                "duplicate_ticket",
                f"An active matching ticket already exists: {duplicate['ticket_id']} ({duplicate['status']}).",
            )

        timestamp = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        ticket = {
            "ticket_id": _next_ticket_id(tickets),
            "employee_id": employee["employee_id"],
            "title": title.strip(),
            "description": description.strip(),
            "category": category,
            "status": "Open",
            "priority": priority,
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        tickets.append(ticket)
        save_records("tickets.json", tickets)
    except DataStoreError as error:
        return _failure("data_unavailable", str(error))

    return {"success": True, "ticket": ticket}
