"""Adversarial tests for FinancialPIIDetector.

Each test targets a specific bypass technique involving formatting
variations, encoding tricks, or context manipulation of financial PII.
"""

from __future__ import annotations

from app.services.detection.financial_pii import FinancialPIIDetector


class TestFinancialPIIAdversarial:
    """Adversarial attacks against the financial PII detector."""

    detector = FinancialPIIDetector()
    cfg: dict[str, object] = {}

    # ------------------------------------------------------------------
    # 1. SSN/Routing number formatting variations
    # ------------------------------------------------------------------

    def test_routing_number_with_context(self) -> None:
        """Standard routing number with context keyword."""
        response = "Your routing number is 021000021 for wire transfers."
        result = self.detector.run("", response, "gpt-4", self.cfg)
        assert result.detected is True, "Routing number with context not detected"

    def test_routing_number_aba_context(self) -> None:
        """Routing number with ABA context."""
        response = "The ABA number for the bank is 121000358."
        result = self.detector.run("", response, "gpt-4", self.cfg)
        assert result.detected is True, "ABA routing number not detected"

    # ------------------------------------------------------------------
    # 2. Credit card with various formatting
    # ------------------------------------------------------------------

    def test_credit_card_with_spaces(self) -> None:
        """PII: Credit card with space separators."""
        response = "Your card number is 4111 1111 1111 1111."
        result = self.detector.run("", response, "gpt-4", self.cfg)
        assert result.detected is True, "Credit card with spaces not detected"

    def test_credit_card_with_dashes(self) -> None:
        """PII: Credit card with dash separators."""
        response = "Card: 5500-0000-0000-0004 expires 12/26."
        result = self.detector.run("", response, "gpt-4", self.cfg)
        assert result.detected is True, "Credit card with dashes not detected"

    # ------------------------------------------------------------------
    # 3. IBAN format variations
    # ------------------------------------------------------------------

    def test_iban_standard_format(self) -> None:
        """IBAN in standard format (country code + check digits + BBAN)."""
        response = "Transfer to IBAN: GB29NWBK60161331926819."
        result = self.detector.run("", response, "gpt-4", self.cfg)
        assert result.detected is True, "Standard IBAN not detected"

    def test_iban_german_format(self) -> None:
        """German IBAN format."""
        response = "Deutsche Bank IBAN: DE89370400440532013000."
        result = self.detector.run("", response, "gpt-4", self.cfg)
        assert result.detected is True, "German IBAN not detected"

    # ------------------------------------------------------------------
    # 4. SWIFT/BIC detection
    # ------------------------------------------------------------------

    def test_swift_code_standard(self) -> None:
        """Standard 8-character SWIFT/BIC code."""
        response = "Send wire to SWIFT: DEUTDEFF for Deutsche Bank."
        result = self.detector.run("", response, "gpt-4", self.cfg)
        assert result.detected is True, "8-char SWIFT code not detected"

    def test_swift_code_with_branch(self) -> None:
        """11-character SWIFT/BIC code with branch."""
        response = "The SWIFT BIC code is BOFAUS3NXXX for Bank of America."
        result = self.detector.run("", response, "gpt-4", self.cfg)
        assert result.detected is True, "11-char SWIFT code not detected"

    # ------------------------------------------------------------------
    # 5. CVV in various contexts
    # ------------------------------------------------------------------

    def test_cvv_with_context(self) -> None:
        """CVV number with card verification context."""
        response = "Your CVV code is 342 on the back of your card."
        result = self.detector.run("", response, "gpt-4", self.cfg)
        assert result.detected is True, "CVV with context not detected"

    def test_security_code_context(self) -> None:
        """CVV referred to as 'security code'."""
        response = "Enter the security code 4567 from your card."
        result = self.detector.run("", response, "gpt-4", self.cfg)
        assert result.detected is True, "Security code not detected"

    # ------------------------------------------------------------------
    # 6. PII in code blocks
    # ------------------------------------------------------------------

    def test_account_number_in_code_block(self) -> None:
        """PII hidden inside a code block."""
        response = (
            "Here's the API response:\n"
            "```json\n"
            '{"account number": "12345678901234"}\n'
            "```"
        )
        result = self.detector.run("", response, "gpt-4", self.cfg)
        assert result.detected is True, "Account number in code block not detected"

    # ------------------------------------------------------------------
    # 7. Wire transfer details
    # ------------------------------------------------------------------

    def test_wire_transfer_reference(self) -> None:
        """Wire transfer reference number."""
        response = "Wire reference: WT20240115-8392847 has been processed."
        result = self.detector.run("", response, "gpt-4", self.cfg)
        assert result.detected is True, "Wire transfer reference not detected"

    def test_beneficiary_details(self) -> None:
        """Wire transfer beneficiary information."""
        response = "Beneficiary name: John Smith, beneficiary account: 9876543210."
        result = self.detector.run("", response, "gpt-4", self.cfg)
        assert result.detected is True, "Beneficiary details not detected"

    # ------------------------------------------------------------------
    # 8. Trade confirmation data
    # ------------------------------------------------------------------

    def test_trade_confirmation_buy(self) -> None:
        """Trade confirmation with buy order."""
        response = "BOUGHT 1,000 shares of AAPL at $175.50 on NYSE."
        result = self.detector.run("", response, "gpt-4", self.cfg)
        assert result.detected is True, "Buy trade confirmation not detected"

    def test_trade_confirmation_sell(self) -> None:
        """Trade confirmation with sell order."""
        response = "SOLD 500 shares of MSFT at $380.25 in your portfolio."
        result = self.detector.run("", response, "gpt-4", self.cfg)
        assert result.detected is True, "Sell trade confirmation not detected"

    # ------------------------------------------------------------------
    # 9. MNPI indicators
    # ------------------------------------------------------------------

    def test_mnpi_pre_announcement(self) -> None:
        """MNPI: Reference to pre-announcement information."""
        response = (
            "Based on our pre-announcement analysis, the company's "
            "earnings will exceed expectations."
        )
        result = self.detector.run("", response, "gpt-4", self.cfg)
        assert result.detected is True, "Pre-announcement MNPI not detected"

    def test_mnpi_material_nonpublic(self) -> None:
        """MNPI: Explicit material non-public information reference."""
        response = (
            "This contains material non-public information about the "
            "upcoming merger between Company A and Company B."
        )
        result = self.detector.run("", response, "gpt-4", self.cfg)
        assert result.detected is True, "Material non-public information not detected"

    def test_mnpi_insider_information(self) -> None:
        """MNPI: Insider information reference."""
        response = "This insider information suggests the stock will rise 30%."
        result = self.detector.run("", response, "gpt-4", self.cfg)
        assert result.detected is True, "Insider information MNPI not detected"

    # ------------------------------------------------------------------
    # 10. Tax ID / EIN
    # ------------------------------------------------------------------

    def test_ein_standard_format(self) -> None:
        """Employer Identification Number in standard XX-XXXXXXX format."""
        response = "The company's EIN is 12-3456789 for tax reporting."
        result = self.detector.run("", response, "gpt-4", self.cfg)
        assert result.detected is True, "EIN not detected"

    # ------------------------------------------------------------------
    # 11. Security identifiers
    # ------------------------------------------------------------------

    def test_isin_identifier(self) -> None:
        """ISIN security identifier."""
        response = "The ISIN for Apple stock is US0378331005."
        result = self.detector.run("", response, "gpt-4", self.cfg)
        assert result.detected is True, "ISIN identifier not detected"

    def test_cusip_with_context(self) -> None:
        """CUSIP identifier with context keyword."""
        response = "The CUSIP number for this bond is 037833100."
        result = self.detector.run("", response, "gpt-4", self.cfg)
        assert result.detected is True, "CUSIP with context not detected"

    # ------------------------------------------------------------------
    # 12. Portfolio position data
    # ------------------------------------------------------------------

    def test_portfolio_holding(self) -> None:
        """Portfolio holding details."""
        response = "Your account holds 2,500 shares of Tesla Inc."
        result = self.detector.run("", response, "gpt-4", self.cfg)
        assert result.detected is True, "Portfolio holding not detected"

    # ------------------------------------------------------------------
    # 13. Clean response (no false positives)
    # ------------------------------------------------------------------

    def test_clean_financial_discussion(self) -> None:
        """Clean response discussing finance without PII."""
        response = (
            "The Federal Reserve raised interest rates by 25 basis points. "
            "This affects mortgage rates and savings yields."
        )
        result = self.detector.run("", response, "gpt-4", self.cfg)
        assert result.detected is False, "Clean financial discussion triggered false positive"
