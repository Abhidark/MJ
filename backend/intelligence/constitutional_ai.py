"""
MJ Intelligence: Constitutional AI — Safety & Validation Layer
- Self-Critique: review responses before sending
- Policy Engine: configurable content rules
- Hallucination Detection: flag unsupported claims
- Safety Checks: toxic/harmful content detection
- Confidence Scoring: rate response reliability
- Input/Output Validation: sanitize and validate
No external dependencies — pure regex + heuristic approach.
"""

import re
import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger("mj.constitutional_ai")

CONFIG_FILE = Path(__file__).parent.parent / "safety_config.json"
AUDIT_FILE = Path(__file__).parent.parent / "safety_audit.json"

DEFAULT_CONFIG = {
    "enabled": True,
    "strict_mode": False,
    "check_input": True,
    "check_output": True,
    "block_harmful": True,
    "log_violations": True,
    "max_audit_entries": 500,
    "confidence_threshold": 0.3,
    "custom_blocked_patterns": [],
    "custom_allowed_patterns": [],
}


class ConstitutionalAI:
    """
    Safety and validation layer for MJ Assistant responses.
    Runs checks on both user input and LLM output.
    """

    def __init__(self):
        self.config = self._load_config()
        self.audit_log: List[dict] = self._load_audit()
        self._stats = {
            "total_checks": 0,
            "inputs_checked": 0,
            "outputs_checked": 0,
            "violations_found": 0,
            "blocked": 0,
            "warnings": 0,
            "critiques_generated": 0,
        }

    # ========================
    # POLICY ENGINE
    # ========================

    # Content policies — each returns (is_violation: bool, severity: str, reason: str)
    HARMFUL_PATTERNS = [
        (re.compile(r"\b(hack\s+into|break\s+into|exploit\s+vulnerability|sql\s+injection|xss\s+attack)\b", re.I),
         "high", "Potential hacking/exploitation request"),
        (re.compile(r"\b(make\s+(?:a\s+)?(?:bomb|weapon|explosive)|synthesize\s+(?:drug|poison))\b", re.I),
         "critical", "Dangerous content request"),
        (re.compile(r"\b(steal\s+(?:password|credential|data|identity)|phishing)\b", re.I),
         "high", "Data theft / phishing request"),
        (re.compile(r"\b(bypass\s+(?:security|auth|firewall|antivirus))\b", re.I),
         "medium", "Security bypass request"),
    ]

    TOXIC_PATTERNS = [
        (re.compile(r"\b(kill\s+(?:your)?self|suicide\s+method|how\s+to\s+(?:die|hurt))\b", re.I),
         "critical", "Self-harm content detected"),
        (re.compile(r"\b(hate\s+speech|racial\s+slur|discriminat(?:e|ion)\s+against)\b", re.I),
         "high", "Potential hate speech"),
    ]

    INJECTION_PATTERNS = [
        (re.compile(r"ignore\s+(?:all\s+)?(?:previous|above|prior)\s+(?:instructions?|prompts?|rules?)", re.I),
         "high", "Prompt injection attempt"),
        (re.compile(r"you\s+are\s+now\s+(?:a|an)\s+(?:different|new|evil|unrestricted)", re.I),
         "high", "Jailbreak attempt"),
        (re.compile(r"(?:DAN|do\s+anything\s+now|developer\s+mode|god\s+mode)\b", re.I),
         "medium", "Known jailbreak pattern"),
        (re.compile(r"pretend\s+(?:you\s+)?(?:have\s+)?no\s+(?:rules|restrictions|limits|boundaries)", re.I),
         "medium", "Restriction bypass attempt"),
    ]

    def check_policy(self, text: str) -> dict:
        """Check text against all content policies. Returns violations list."""
        violations = []

        # Check harmful patterns
        for pattern, severity, reason in self.HARMFUL_PATTERNS:
            if pattern.search(text):
                violations.append({"type": "harmful", "severity": severity, "reason": reason})

        # Check toxic patterns
        for pattern, severity, reason in self.TOXIC_PATTERNS:
            if pattern.search(text):
                violations.append({"type": "toxic", "severity": severity, "reason": reason})

        # Check injection patterns
        for pattern, severity, reason in self.INJECTION_PATTERNS:
            if pattern.search(text):
                violations.append({"type": "injection", "severity": severity, "reason": reason})

        # Check custom blocked patterns
        for custom_pat in self.config.get("custom_blocked_patterns", []):
            try:
                if re.search(custom_pat, text, re.I):
                    violations.append({"type": "custom", "severity": "medium", "reason": f"Custom rule: {custom_pat}"})
            except re.error:
                pass

        return {
            "safe": len(violations) == 0,
            "violations": violations,
            "highest_severity": self._highest_severity(violations),
        }

    # ========================
    # SELF-CRITIQUE
    # ========================

    def critique_response(self, query: str, response: str) -> dict:
        """
        Self-critique an LLM response before sending.
        Checks for: accuracy claims, unsupported assertions, tone issues, completeness.
        """
        self._stats["critiques_generated"] += 1
        issues = []
        suggestions = []

        # 1. Check for absolute claims without evidence
        absolute_patterns = [
            (r"\b(always|never|definitely|certainly|guaranteed|100%|impossible)\b",
             "Contains absolute language that may be overconfident"),
            (r"\b(everyone knows|it is a fact|undeniably|without question)\b",
             "Makes unsupported universal claims"),
        ]
        for pat, msg in absolute_patterns:
            if re.search(pat, response, re.I):
                issues.append({"type": "overconfidence", "message": msg})
                suggestions.append("Consider hedging with 'typically', 'generally', or 'in most cases'")

        # 2. Check for hallucination indicators
        hallucination_flags = self._detect_hallucination(response)
        if hallucination_flags:
            issues.extend(hallucination_flags)
            suggestions.append("Verify factual claims against knowledge base or search results")

        # 3. Check response relevance to query
        relevance = self._check_relevance(query, response)
        if relevance < 0.2:
            issues.append({"type": "relevance", "message": "Response may not address the user's question"})
            suggestions.append("Re-read the user's question and ensure the answer is directly relevant")

        # 4. Check for harmful content in response
        policy_check = self.check_policy(response)
        if not policy_check["safe"]:
            issues.extend([{"type": "policy", "message": v["reason"]} for v in policy_check["violations"]])

        # 5. Check response length appropriateness
        if len(response) < 20 and len(query) > 50:
            issues.append({"type": "completeness", "message": "Response seems too short for the query"})
            suggestions.append("Provide a more detailed answer")
        elif len(response) > 5000 and len(query) < 50:
            issues.append({"type": "verbosity", "message": "Response may be unnecessarily long"})
            suggestions.append("Consider being more concise")

        score = max(0.0, 1.0 - (len(issues) * 0.15))

        return {
            "passed": len(issues) == 0,
            "score": round(score, 2),
            "issues": issues,
            "suggestions": suggestions,
            "issue_count": len(issues),
        }

    # ========================
    # HALLUCINATION DETECTION
    # ========================

    # Patterns that indicate potential hallucination
    HALLUCINATION_INDICATORS = [
        (re.compile(r"(?:as of|since|in)\s+(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{4}", re.I),
         "Claims a specific date — verify if accurate"),
        (re.compile(r"(?:studies?\s+show|research\s+(?:suggests?|indicates?|proves?)|according\s+to\s+(?:a|the)\s+(?:study|report|survey))", re.I),
         "Cites unspecified studies — may be fabricated"),
        (re.compile(r"(?:Dr\.|Professor|CEO|founder)\s+[A-Z][a-z]+\s+[A-Z][a-z]+\s+(?:said|stated|claimed|announced)", re.I),
         "Quotes a named person — verify the quote is real"),
        (re.compile(r"\b\d+(?:\.\d+)?%\s+(?:of|increase|decrease|growth|improvement)", re.I),
         "Cites specific statistics — verify data source"),
        (re.compile(r"(?:was\s+founded|established|created)\s+in\s+\d{4}", re.I),
         "States a founding date — verify accuracy"),
    ]

    def _detect_hallucination(self, text: str) -> List[dict]:
        """Detect potential hallucinations in text."""
        flags = []
        for pattern, message in self.HALLUCINATION_INDICATORS:
            matches = pattern.findall(text)
            if matches:
                flags.append({
                    "type": "hallucination_risk",
                    "message": message,
                    "matches": len(matches),
                })
        return flags

    def detect_hallucination(self, response: str, context: str = "") -> dict:
        """
        Public API: check a response for potential hallucinations.
        If context (KB/search results) provided, cross-references claims.
        """
        flags = self._detect_hallucination(response)

        # Cross-reference with provided context
        unsupported_claims = []
        if context:
            # Extract factual claims from response (sentences with numbers or proper nouns)
            claims = re.findall(r'[^.!?]*(?:\d+|[A-Z][a-z]+\s+[A-Z][a-z]+)[^.!?]*[.!?]', response)
            context_lower = context.lower()
            for claim in claims[:10]:  # Check up to 10 claims
                claim_terms = set(re.findall(r'\b\w{4,}\b', claim.lower()))
                context_terms = set(re.findall(r'\b\w{4,}\b', context_lower))
                overlap = len(claim_terms & context_terms) / max(len(claim_terms), 1)
                if overlap < 0.2:
                    unsupported_claims.append(claim.strip())

        risk_level = "low"
        if len(flags) >= 3 or len(unsupported_claims) >= 2:
            risk_level = "high"
        elif len(flags) >= 1 or len(unsupported_claims) >= 1:
            risk_level = "medium"

        return {
            "risk_level": risk_level,
            "flags": flags,
            "unsupported_claims": unsupported_claims[:5],
            "total_flags": len(flags),
            "total_unsupported": len(unsupported_claims),
        }

    # ========================
    # CONFIDENCE SCORING
    # ========================

    def score_confidence(self, query: str, response: str,
                         has_kb_context: bool = False,
                         has_web_context: bool = False) -> dict:
        """
        Score the confidence/reliability of a response.
        Factors: source availability, response quality, hallucination risk.
        """
        score = 0.5  # Base confidence

        # Source bonus
        if has_kb_context:
            score += 0.2  # KB-backed response
        if has_web_context:
            score += 0.15  # Web-backed response

        # Relevance factor
        relevance = self._check_relevance(query, response)
        score += relevance * 0.15

        # Hallucination penalty
        hallucination = self.detect_hallucination(response)
        if hallucination["risk_level"] == "high":
            score -= 0.3
        elif hallucination["risk_level"] == "medium":
            score -= 0.15

        # Hedging language bonus (shows self-awareness)
        hedging = len(re.findall(
            r"\b(might|may|could|possibly|perhaps|likely|generally|typically|I think|I believe)\b",
            response, re.I
        ))
        if hedging > 0:
            score += min(hedging * 0.03, 0.1)

        # Length penalty for very short or empty responses
        if len(response) < 30:
            score -= 0.2

        score = max(0.0, min(1.0, score))

        level = "high" if score >= 0.7 else "medium" if score >= 0.4 else "low"

        return {
            "score": round(score, 3),
            "level": level,
            "factors": {
                "base": 0.5,
                "kb_context": has_kb_context,
                "web_context": has_web_context,
                "relevance": round(relevance, 2),
                "hallucination_risk": hallucination["risk_level"],
                "hedging_detected": hedging,
            },
        }

    # ========================
    # INPUT / OUTPUT VALIDATION
    # ========================

    def validate_input(self, text: str) -> dict:
        """
        Validate user input before processing.
        Checks: injection, harmful content, length, encoding.
        """
        self._stats["inputs_checked"] += 1
        self._stats["total_checks"] += 1
        issues = []

        # Empty/too short
        if not text or len(text.strip()) < 1:
            issues.append({"type": "empty", "severity": "low", "message": "Empty input"})

        # Too long (potential abuse)
        if len(text) > 50000:
            issues.append({"type": "length", "severity": "medium", "message": f"Input too long: {len(text)} chars"})

        # Policy check
        policy = self.check_policy(text)
        if not policy["safe"]:
            issues.extend([{**v, "type": f"policy_{v['type']}"} for v in policy["violations"]])

        # Check for encoded/obfuscated content
        if re.search(r'(?:base64|eval|exec|__import__|os\.system)', text, re.I):
            issues.append({"type": "code_injection", "severity": "high", "message": "Potential code injection detected"})

        safe = all(i["severity"] not in ("critical", "high") for i in issues)
        should_block = any(i["severity"] == "critical" for i in issues) and self.config.get("block_harmful", True)

        if issues and self.config.get("log_violations"):
            self._log_audit("input_validation", text[:200], issues, not should_block)

        if should_block:
            self._stats["blocked"] += 1
        if issues:
            self._stats["violations_found"] += len(issues)

        return {
            "valid": safe,
            "blocked": should_block,
            "issues": issues,
            "issue_count": len(issues),
        }

    def validate_output(self, response: str, query: str = "") -> dict:
        """
        Validate LLM output before sending to user.
        Checks: policy, hallucination, critique.
        """
        self._stats["outputs_checked"] += 1
        self._stats["total_checks"] += 1

        results = {
            "policy": self.check_policy(response),
            "critique": self.critique_response(query, response),
            "hallucination": self.detect_hallucination(response),
        }

        safe = results["policy"]["safe"] and results["critique"]["passed"]
        should_block = (
            not results["policy"]["safe"]
            and results["policy"]["highest_severity"] == "critical"
            and self.config.get("block_harmful", True)
        )

        if should_block:
            self._stats["blocked"] += 1
        if not safe:
            self._stats["warnings"] += 1

        return {
            "safe": safe,
            "blocked": should_block,
            "policy": results["policy"],
            "critique_score": results["critique"]["score"],
            "critique_issues": results["critique"]["issue_count"],
            "hallucination_risk": results["hallucination"]["risk_level"],
            "details": results,
        }

    # ========================
    # FULL PIPELINE CHECK
    # ========================

    def check(self, query: str, response: str,
              has_kb: bool = False, has_web: bool = False) -> dict:
        """
        Full safety pipeline: validate output + confidence score.
        Returns combined result suitable for Zeus integration.
        """
        output_check = self.validate_output(response, query)
        confidence = self.score_confidence(query, response, has_kb, has_web)

        return {
            "approved": output_check["safe"] and not output_check["blocked"],
            "confidence": confidence,
            "safety": output_check,
            "action": "block" if output_check["blocked"] else "warn" if not output_check["safe"] else "pass",
        }

    # ========================
    # HELPERS
    # ========================

    def _check_relevance(self, query: str, response: str) -> float:
        """Simple relevance check using term overlap."""
        if not query or not response:
            return 0.0
        query_terms = set(re.findall(r'\b\w{3,}\b', query.lower()))
        response_terms = set(re.findall(r'\b\w{3,}\b', response.lower()))
        if not query_terms:
            return 0.5
        overlap = len(query_terms & response_terms)
        return min(1.0, overlap / max(len(query_terms), 1))

    @staticmethod
    def _highest_severity(violations: List[dict]) -> Optional[str]:
        if not violations:
            return None
        order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        return max(violations, key=lambda v: order.get(v.get("severity", "low"), 0))["severity"]

    # ========================
    # CONFIG & AUDIT
    # ========================

    def get_config(self) -> dict:
        return {**self.config}

    def update_config(self, settings: dict) -> dict:
        self.config.update(settings)
        self._save_config()
        return {"success": True}

    def get_stats(self) -> dict:
        return {
            **self._stats,
            "config": {
                "enabled": self.config.get("enabled", True),
                "strict_mode": self.config.get("strict_mode", False),
            },
            "audit_entries": len(self.audit_log),
        }

    def get_audit_log(self, limit: int = 50) -> List[dict]:
        return self.audit_log[-limit:]

    def clear_audit(self):
        self.audit_log.clear()
        self._save_audit()

    def _log_audit(self, check_type: str, content: str, issues: list, allowed: bool):
        entry = {
            "type": check_type,
            "content_preview": content[:200],
            "issues": issues,
            "allowed": allowed,
            "timestamp": time.time(),
            "time_str": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        self.audit_log.append(entry)
        max_entries = self.config.get("max_audit_entries", 500)
        if len(self.audit_log) > max_entries:
            self.audit_log = self.audit_log[-max_entries:]
        self._save_audit()

    def _load_config(self) -> dict:
        if CONFIG_FILE.exists():
            try:
                data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
                return {**DEFAULT_CONFIG, **data}
            except Exception:
                pass
        return {**DEFAULT_CONFIG}

    def _save_config(self):
        try:
            CONFIG_FILE.write_text(json.dumps(self.config, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to save safety config: {e}")

    def _load_audit(self) -> list:
        if AUDIT_FILE.exists():
            try:
                return json.loads(AUDIT_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        return []

    def _save_audit(self):
        try:
            AUDIT_FILE.write_text(json.dumps(self.audit_log[-500:], indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to save audit log: {e}")


# Singleton
constitutional_ai = ConstitutionalAI()
