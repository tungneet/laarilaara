"""Admin billing/support service (catalog §15 "Billing/support").

Subscriptions/transactions listings are read-only admin views over the
existing §13 billing repository. Support tickets are a new resource with a
real, directly-reachable create path (see `support_tickets.py` docstring).
"""
from __future__ import annotations

from app.repositories import admin_audit as admin_audit_repo
from app.repositories import billing as billing_repo
from app.repositories import support_tickets as support_tickets_repo


class SupportTicketNotFoundError(Exception):
    pass


def list_subscriptions() -> list[dict]:
    return billing_repo.list_all_subscriptions()


def list_transactions() -> list[dict]:
    return billing_repo.list_all_transactions()


def list_support_tickets(status_filter: str | None) -> list[dict]:
    return support_tickets_repo.list_tickets(status_filter)


def create_support_ticket(admin_account_id: str, account_id: str | None, subject: str, body: str) -> dict:
    return support_tickets_repo.create_ticket(account_id, subject, body)


def get_support_ticket(ticket_id: str) -> dict:
    ticket = support_tickets_repo.get_ticket(ticket_id)
    if ticket is None:
        raise SupportTicketNotFoundError(ticket_id)
    return ticket


def update_support_ticket(admin_account_id: str, ticket_id: str, new_status: str, reason: str) -> dict:
    get_support_ticket(ticket_id)  # raises SupportTicketNotFoundError if missing
    updated = support_tickets_repo.update_status(ticket_id, new_status)
    admin_audit_repo.record(
        admin_account_id, f"support.ticket.status.{new_status}", "support_ticket", ticket_id, reason
    )
    return updated
