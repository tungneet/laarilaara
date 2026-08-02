"""Admin dashboard service (catalog §15 "Dashboard": `GET /v1/admin/dashboard`,
`GET /v1/admin/health/queues`).

No real metrics/observability stack or SQS queues exist anywhere in this
codebase (everything is a single Lambda + DynamoDB, no async workers) so
both endpoints are synthesized aggregate views over existing repositories
rather than pulling from CloudWatch/SQS — documented simplification, same
class of gap as `webhooks.py`'s "no worker" pattern.
"""
from __future__ import annotations

from app.domain.profiles import ProfileStatus
from app.repositories import accounts as accounts_repo
from app.repositories import moderation_cases as moderation_cases_repo
from app.repositories import profiles as profiles_repo
from app.repositories import support_tickets as support_tickets_repo
from app.repositories import verification_requests as verification_requests_repo


def get_dashboard() -> dict:
    accounts = accounts_repo.list_all_accounts()
    profiles = profiles_repo.list_all_profiles()
    published = [p for p in profiles if p.status == ProfileStatus.PUBLISHED]
    open_cases = moderation_cases_repo.list_cases(status_filter="open")
    assigned_cases = moderation_cases_repo.list_cases(status_filter="assigned")
    submitted_requests = verification_requests_repo.list_all_requests(status_filter="submitted")
    open_tickets = support_tickets_repo.list_tickets(status_filter="open")
    return {
        "account_count": len(accounts),
        "profile_count": len(profiles),
        "published_profile_count": len(published),
        "open_moderation_case_count": len(open_cases) + len(assigned_cases),
        "submitted_verification_request_count": len(submitted_requests),
        "open_support_ticket_count": len(open_tickets),
    }


def get_queue_health() -> dict:
    """Proxy signal for queue depth (catalog: `GET /v1/admin/health/queues`).

    There are no real SQS queues provisioned/referenced in this codebase, so
    each "queue" below reports the count of a corresponding "queued forever,
    no worker" resource as a documented stand-in for a real queue depth
    metric.
    """
    verification_requests = verification_requests_repo.list_all_requests(status_filter="submitted")
    support_tickets = support_tickets_repo.list_tickets(status_filter="open")
    moderation_cases = moderation_cases_repo.list_cases(status_filter="open")
    return {
        "queues": [
            {"name": "verification-requests", "depth": len(verification_requests), "status": "ok"},
            {"name": "support-tickets", "depth": len(support_tickets), "status": "ok"},
            {"name": "moderation-cases", "depth": len(moderation_cases), "status": "ok"},
        ]
    }
