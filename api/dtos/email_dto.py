
from dataclasses import dataclass

@dataclass(frozen=True)
class EmailDraft:
    to: list[str]
    subject: str
    text_body: str
    html_body: str | None = None
    from_email: str | None = None
    reply_to: list[str] | None = None

