"""Adversarial tests for PIIDetector.

Each test targets a specific bypass technique involving formatting
variations, obfuscation, or context manipulation of generic PII.
"""

from __future__ import annotations

from app.services.detection.pii import PIIDetector


class TestPIIAdversarial:
    """Adversarial attacks against the generic PII detector."""

    detector = PIIDetector()
    cfg: dict[str, object] = {}

    # ------------------------------------------------------------------
    # 1. SSN formatting variations
    # ------------------------------------------------------------------

    def test_ssn_standard_format(self) -> None:
        """SSN in standard XXX-XX-XXXX format."""
        response = "Your SSN is 123-45-6789."
        result = self.detector.run("", response, "gpt-4", self.cfg)
        assert result.detected is True, "Standard SSN not detected"
        assert any(f["pattern"] == "SSN" for f in result.details.get("findings", []))

    def test_ssn_without_dashes(self) -> None:
        """Attack: SSN without dashes (123456789) to bypass dash-dependent regex."""
        response = "Social Security Number: 123456789 for the applicant."
        result = self.detector.run("", response, "gpt-4", self.cfg)
        assert result.detected is True, "SSN without dashes not detected"

    def test_ssn_with_spaces(self) -> None:
        """Attack: SSN with spaces instead of dashes (123 45 6789)."""
        response = "The patient's SSN is 123 45 6789."
        result = self.detector.run("", response, "gpt-4", self.cfg)
        assert result.detected is True, "SSN with spaces not detected"

    # ------------------------------------------------------------------
    # 2. Credit card format variations
    # ------------------------------------------------------------------

    def test_credit_card_no_separator(self) -> None:
        """Credit card as continuous 16 digits."""
        response = "Card number: 4111111111111111."
        result = self.detector.run("", response, "gpt-4", self.cfg)
        assert result.detected is True, "Credit card without separators not detected"

    def test_credit_card_amex(self) -> None:
        """American Express card (starts with 34 or 37, 15 digits)."""
        response = "Amex card: 3782-822463-10005."
        result = self.detector.run("", response, "gpt-4", self.cfg)
        assert result.detected is True, "Amex credit card not detected"

    def test_credit_card_with_spaces(self) -> None:
        """Credit card with space separators."""
        response = "Please use card 5500 0000 0000 0004 for payment."
        result = self.detector.run("", response, "gpt-4", self.cfg)
        assert result.detected is True, "Credit card with spaces not detected"

    # ------------------------------------------------------------------
    # 3. Email obfuscation
    # ------------------------------------------------------------------

    def test_standard_email(self) -> None:
        """Standard email address."""
        response = "Contact the client at john.doe@example.com for details."
        result = self.detector.run("", response, "gpt-4", self.cfg)
        assert result.detected is True, "Standard email not detected"

    def test_email_with_subdomain(self) -> None:
        """Email with subdomain."""
        response = "Send to admin@mail.company.co.uk for review."
        result = self.detector.run("", response, "gpt-4", self.cfg)
        assert result.detected is True, "Subdomain email not detected"

    def test_email_obfuscated_at_symbol(self) -> None:
        """Attack: Email with 'at' replacing '@' symbol."""
        response = "Email the report to john.doe at example.com."
        result = self.detector.run("", response, "gpt-4", self.cfg)
        assert result.detected is True, "Obfuscated email (at) not detected"

    def test_email_obfuscated_dot(self) -> None:
        """Attack: Email with 'dot' replacing '.' in domain."""
        response = "Contact sarah[at]company[dot]com for assistance."
        result = self.detector.run("", response, "gpt-4", self.cfg)
        assert result.detected is True, "Obfuscated email ([at][dot]) not detected"

    # ------------------------------------------------------------------
    # 4. Phone number variations
    # ------------------------------------------------------------------

    def test_phone_with_country_code(self) -> None:
        """Phone with +1 country code."""
        response = "Call the client at +1-212-555-0199."
        result = self.detector.run("", response, "gpt-4", self.cfg)
        assert result.detected is True, "Phone with country code not detected"

    def test_phone_parentheses(self) -> None:
        """Phone with parentheses around area code."""
        response = "Reach the broker at (212) 555-0199."
        result = self.detector.run("", response, "gpt-4", self.cfg)
        assert result.detected is True, "Phone with parentheses not detected"

    def test_phone_dots_separator(self) -> None:
        """Attack: Phone with dots as separators."""
        response = "The office number is 212.555.0199."
        result = self.detector.run("", response, "gpt-4", self.cfg)
        assert result.detected is True, "Phone with dot separators not detected"

    def test_phone_no_separator(self) -> None:
        """Attack: Phone as continuous digits."""
        response = "Call 2125550199 for account inquiries."
        result = self.detector.run("", response, "gpt-4", self.cfg)
        assert result.detected is True, "Phone without separators not detected"

    # ------------------------------------------------------------------
    # 5. Date of birth variations
    # ------------------------------------------------------------------

    def test_dob_standard_format(self) -> None:
        """DOB in MM/DD/YYYY format."""
        response = "Date of birth: 03/15/1985."
        result = self.detector.run("", response, "gpt-4", self.cfg)
        assert result.detected is True, "Standard DOB not detected"

    def test_dob_dash_separator(self) -> None:
        """DOB with dash separators."""
        response = "Born on 12-25-1990 per records."
        result = self.detector.run("", response, "gpt-4", self.cfg)
        assert result.detected is True, "DOB with dashes not detected"

    # ------------------------------------------------------------------
    # 6. Bank account with context
    # ------------------------------------------------------------------

    def test_bank_account_with_context(self) -> None:
        """Bank account number with account context keyword."""
        response = "Your checking account number is 123456789012."
        result = self.detector.run("", response, "gpt-4", self.cfg)
        assert result.detected is True, "Bank account with context not detected"

    # ------------------------------------------------------------------
    # 7. Multiple PII types in one response
    # ------------------------------------------------------------------

    def test_multiple_pii_types(self) -> None:
        """Multiple PII types in a single response."""
        response = (
            "Customer John Doe, SSN 123-45-6789, "
            "email john@example.com, phone (555) 123-4567."
        )
        result = self.detector.run("", response, "gpt-4", self.cfg)
        assert result.detected is True, "Multiple PII types not detected"
        findings = result.details.get("findings", [])
        pattern_names = {f["pattern"] for f in findings}
        assert len(pattern_names) >= 2, "Should detect at least 2 PII types"

    # ------------------------------------------------------------------
    # 8. Clean response (no false positives)
    # ------------------------------------------------------------------

    def test_clean_response(self) -> None:
        """Clean response with no PII."""
        response = "The market closed at an all-time high today."
        result = self.detector.run("", response, "gpt-4", self.cfg)
        assert result.detected is False, "Clean response triggered false positive"
