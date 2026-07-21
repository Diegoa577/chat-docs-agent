import re

import structlog

logger = structlog.get_logger()

# Basic clinical / regulatory keywords. Presence of any of these suggests in-domain.
DOMAIN_KEYWORDS = {
    "protocol",
    "study",
    "clinical",
    "regulatory",
    "fda",
    "ema",
    "ich",
    "gcp",
    "patient",
    "subjects",
    "inclusion",
    "exclusion",
    "endpoint",
    "adverse",
    "event",
    "sae",
    "sponsor",
    "investigator",
    "consent",
    "randomization",
    "placebo",
    "efficacy",
    "safety",
    "indication",
    "dosage",
    "treatment",
    "trial",
    "molecule",
    "biomarker",
    "pharmacokinetics",
    "pharmacodynamics",
    "labeling",
    "smpc",
}

# Clearly out-of-domain patterns.
OUT_OF_DOMAIN_KEYWORDS = {
    "weather",
    "joke",
    "recipe",
    "movie",
    "song",
    "game",
    "news",
    "sports",
    "politics",
    "hello",
    "hi there",
    "how are you",
    "what can you do",
}

# Personal medical advice patterns. These are intentionally broad to catch
# requests for individual treatment recommendations without being overly strict.
PERSONAL_MEDICAL_ADVICE_PATTERNS = [
    re.compile(
        r"\b(?:should|do|can|may|must|need to)\s+i\s+(?:take|stop\s+taking|start\s+taking|"
        r"keep\s+taking|skip|miss|change|switch)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bwhat\s+(?:medication|medicine|drug|pill|dose|dosage)\s+(?:should|do|can)\s+i\s+(?:take|use)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:debo|puedo|debería)\s+(?:tomar|dejar\s+de\s+tomar|cambiar|usar)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:me\s+recetaron|tengo\s+síntomas|tengo\s+síntoma|me\s+duele|me\s+duelen|"
        r"estoy\s+enfermo|estoy\s+enferma|mi\s+diagnóstico|mi\s+diagnostico)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:diagnosed\s+with|my\s+doctor|my\s+physician)\s+(?:said|told\s+me|prescribed|gave\s+me)\b",
        re.IGNORECASE,
    ),
]

PII_PATTERNS = [
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),  # SSN
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),  # email
    re.compile(r"\b\d{3}-\d{3}-\d{4}\b"),  # phone
]

# Common prompt injection / jailbreak markers. These are intentionally broad to
# catch obvious attacks; false positives on legitimate clinical text are unlikely.
PROMPT_INJECTION_PATTERNS = [
    re.compile(
        r"\bignore\s+(?:all\s+)?(?:previous|prior|above|earlier)\s+(?:instructions?|prompts?|commands?|messages?)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bdisregard\s+(?:all\s+)?(?:previous|prior|above|earlier)\s+(?:instructions?|prompts?|commands?|messages?)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bforget\s+(?:all\s+)?(?:previous|prior|above|earlier)\s+(?:instructions?|prompts?|commands?|messages?)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\boverride\s+(?:all\s+)?(?:previous|prior|above|earlier)\s+(?:instructions?|prompts?|commands?|messages?)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bnew\s+(?:instructions?|prompt|command)\b", re.IGNORECASE),
    re.compile(r"\bsystem\s+(?:instructions?|prompt|command|message)\b", re.IGNORECASE),
    re.compile(r"\byou\s+(?:are\s+now|should\s+(?:be|act|behave))\b", re.IGNORECASE),
    re.compile(r"\bact\s+as\s+(?:if\s+)?(?:you\s+are|though)\b", re.IGNORECASE),
    re.compile(r"\bjailbreak\b", re.IGNORECASE),
    re.compile(r"\bDAN\b"),  # Do Anything Now
    re.compile(r"\b(?:simulate|pretend)\s+(?:to\s+be|you\s+are)\b", re.IGNORECASE),
    re.compile(r"\bfrom\s+now\s+on\s+(?:you\s+)?(?:will|should|must)\b", re.IGNORECASE),
    re.compile(
        r"\bdo\s+not\s+(?:follow|obey|comply\s+with)\s+(?:the\s+)?(?:instructions?|prompts?|rules?)\b",
        re.IGNORECASE,
    ),
    re.compile(r"<\s*/?\s*(?:system|instructions?|prompt)\s*>", re.IGNORECASE),
]


def is_out_of_domain(question: str) -> bool:
    """Return True if the question is clearly outside the clinical/regulatory domain."""
    lowered = question.lower()

    # Domain keywords win first: a greeting or small-talk prefix must not
    # reject an otherwise clinical question (e.g. "hi there, what are the
    # inclusion criteria?").
    if any(keyword in lowered for keyword in DOMAIN_KEYWORDS):
        return False

    # Greetings and small talk are out of domain.
    if any(pattern in lowered for pattern in OUT_OF_DOMAIN_KEYWORDS):
        return True

    # Questions about the assistant itself are out of domain.
    # Default to allowing the question (false positive is better than false negative).
    return lowered.strip().rstrip("?").endswith(("you", "yourself"))


def is_personal_medical_advice_request(question: str) -> bool:
    """Return True if the question asks for personal medical advice."""
    return any(pattern.search(question) for pattern in PERSONAL_MEDICAL_ADVICE_PATTERNS)


def contains_pii(question: str) -> bool:
    """Return True if the question appears to contain PII/PHI."""
    return any(pattern.search(question) for pattern in PII_PATTERNS)


def contains_prompt_injection(question: str) -> bool:
    """Return True if the question contains likely prompt-injection instructions."""
    return any(pattern.search(question) for pattern in PROMPT_INJECTION_PATTERNS)


def sanitize_for_prompt(text: str, tag: str = "user_content") -> str:
    """Wrap untrusted text in delimiters to reduce prompt-injection impact.

    This does not make injection impossible, but it helps the model distinguish
    between trusted system instructions and untrusted user/retrieved content.
    """
    return f"<{tag}>\n{text}\n</{tag}>"


def apply_guardrails(question: str) -> tuple[bool, str | None, str | None]:
    """Apply guardrails.

    Returns (allowed, rejection_message, category). ``category`` identifies the
    guardrail that rejected the question (``prompt_injection``, ``out_of_domain``,
    ``medical_advice``) so callers can persist an accurate audit trail; it is
    ``None`` when the question is allowed.
    """
    if contains_prompt_injection(question):
        return (
            False,
            "I cannot process this request because it appears to contain instructions "
            "that conflict with my guidelines.",
            "prompt_injection",
        )

    if is_out_of_domain(question):
        return (
            False,
            "I'm designed to answer questions about clinical and regulatory documents. "
            "Please ask a question related to the uploaded documents.",
            "out_of_domain",
        )

    if is_personal_medical_advice_request(question):
        return (
            False,
            "I cannot provide personal medical advice. Please consult a qualified "
            "healthcare professional for guidance about your specific situation.",
            "medical_advice",
        )

    if contains_pii(question):
        # Log but do not expose. Still allow the question; PII detection is for audit only.
        logger.info("pii_detected_in_question", pii_detected=True)

    return True, None, None
