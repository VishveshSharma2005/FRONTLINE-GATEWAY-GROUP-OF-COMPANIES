"""Mock backend the model can call when a message references an existing
support ticket. Demonstrates tool/function-calling: instead of guessing
ticket status from thin air, the model asks for it and grounds its
suggested_action in the real (mocked) data."""

MOCK_TICKETS = {
    "48213": {"status": "open", "assigned_to": "support-tier-1", "last_update_days_ago": 5},
}


def lookup_ticket_status(ticket_id: str) -> dict:
    return MOCK_TICKETS.get(ticket_id, {"status": "not_found"})


TOOL_IMPLS = {"lookup_ticket_status": lookup_ticket_status}

TOOLS_SPEC = [
    {
        "type": "function",
        "function": {
            "name": "lookup_ticket_status",
            "description": (
                "Look up the current status of an existing support ticket by its "
                "ID number. Use this when the customer message references a "
                "previous ticket number and you need its real status instead of "
                "guessing."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "ticket_id": {
                        "type": "string",
                        "description": "The ticket ID number, digits only, e.g. '48213'",
                    }
                },
                "required": ["ticket_id"],
            },
        },
    }
]
