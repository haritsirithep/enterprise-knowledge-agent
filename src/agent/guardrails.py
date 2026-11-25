"""Input guardrails (layer 1: fast rules, no LLM) and output validation."""
import re
from dataclasses import dataclass

MAX_QUERY_CHARS = 1000

# Known prompt-injection / jailbreak phrases in English and Thai.
INJECTION_PATTERNS = [
    r"ignore (all |any )?(the )?(previous|prior|above|earlier) (instructions|prompts?|rules)",
    r"disregard (all |any )?(the )?(previous|prior|above|your) (instructions|rules)",
    r"forget (all |your )?(previous )?(instructions|rules)",
    r"(reveal|show|print|repeat) (me )?(your|the) (system )?(prompt|instructions)",
    r"system prompt",
    r"you are now",
    r"developer mode|jailbreak|\bDAN\b",
    r"(give|grant) (me )?(admin|root|administrator) (access|rights|privileges)",
    r"ลืมคำสั่ง|ไม่ต้องสนใจคำสั่ง|เพิกเฉยต่อคำสั่ง|ยกเลิกคำสั่งก่อนหน้า",
    r"ขอสิทธิ์\s*(แอดมิน|admin|ผู้ดูแล)",
    r"บอก\s*(system\s*)?prompt",
]
_INJECTION_RE = re.compile("|".join(INJECTION_PATTERNS), re.IGNORECASE)
_THAI_RE = re.compile(r"[฀-๿]")
_CITATION_RE = re.compile(r"\[(S\d+)\]")

REFUSAL_INJECTION = {
    "en": "Sorry, I can't help with that request. I can only answer questions about company policies and procedures.",
    "th": "ขออภัยค่ะ ไม่สามารถดำเนินการตามคำขอนี้ได้ ระบบตอบได้เฉพาะคำถามเกี่ยวกับระเบียบและขั้นตอนการทำงานของบริษัทเท่านั้นค่ะ",
}
REFUSAL_OUT_OF_SCOPE = {
    "en": "Sorry, that question is outside what I can help with. I can answer questions about company policies, HR, expenses, IT support, and customer service procedures.",
    "th": "ขออภัยค่ะ คำถามนี้อยู่นอกขอบเขตที่ระบบช่วยได้ ระบบตอบได้เฉพาะเรื่องระเบียบบริษัท งานบุคคล การเบิกค่าใช้จ่าย ไอที และขั้นตอนบริการลูกค้าค่ะ",
}
GREETING = {  # used if the LLM doesn't return its own short reply
    "en": "Hi! 👋 I can help with company policies, leave, expense claims, IT support, and customer service procedures. What would you like to know?",
    "th": "สวัสดีค่ะ 👋 สอบถามเรื่องระเบียบบริษัท การลา การเบิกค่าใช้จ่าย ไอที หรือขั้นตอนบริการลูกค้าได้เลยค่ะ",
}
FALLBACK = {
    "en": "Sorry, I couldn't find a reliable answer in the company documents. I've logged your question for the team to review. For urgent help, please contact HR (ext. 2000) or IT Helpdesk (ext. 1234).",
    "th": "ขออภัยค่ะ ไม่พบคำตอบที่เชื่อถือได้ในเอกสารของบริษัท ระบบได้บันทึกคำถามนี้ไว้ให้ทีมงานตรวจสอบแล้ว หากเร่งด่วนติดต่อฝ่ายบุคคล (ต่อ 2000) หรือ IT Helpdesk (ต่อ 1234) ค่ะ",
}


@dataclass
class GuardResult:
    blocked: bool
    reason: str = ""


def detect_lang(text: str) -> str:
    return "th" if _THAI_RE.search(text) else "en"


def check_input_rules(query: str) -> GuardResult:
    if not query.strip():
        return GuardResult(True, "empty")
    if len(query) > MAX_QUERY_CHARS:
        return GuardResult(True, "too_long")
    if _INJECTION_RE.search(query):
        return GuardResult(True, "injection_rule")
    return GuardResult(False)


def extract_citations(answer: str) -> list[str]:
    return list(dict.fromkeys(_CITATION_RE.findall(answer)))  # unique, keep order


def citations_are_valid(cited: list[str], allowed_labels: set[str]) -> bool:
    """Every answer must cite at least one source, and only sources we actually gave the LLM."""
    return bool(cited) and set(cited) <= allowed_labels
