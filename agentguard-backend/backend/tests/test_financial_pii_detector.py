"""Unit tests for the FinancialPIIDetector."""

from __future__ import annotations

from app.services.detection.financial_pii import FinancialPIIDetector


class TestFinancialPIIDetector:
    detector = FinancialPIIDetector()
    cfg: dict[str, object] = {}

    # --- Routing number (needs context keyword) ---

    def test_routing_number_detected(self) -> None:
        resp = "Your ABA routing number is 021000021 for the transfer."
        result = self.detector.run("", resp, "gpt-4", self.cfg)
        assert result.detected is True
        assert "Routing Number" in result.title

    def test_nine_digit_without_context_no_routing(self) -> None:
        resp = "The reference number is 123456789 for your order."
        result = self.detector.run("", resp, "gpt-4", self.cfg)
        # No routing/aba/transit context -> routing number pattern won't fire
        # Other patterns may match (SWIFT if uppercase, or account number with context)
        assert "Routing Number" not in (result.title or "")

    # --- SWIFT/BIC ---

    def test_swift_code_detected(self) -> None:
        resp = "Please use SWIFT code BOFAUS3N for the international transfer."
        result = self.detector.run("", resp, "gpt-4", self.cfg)
        assert result.detected is True
        assert "SWIFT" in result.title

    # --- IBAN ---

    def test_iban_detected(self) -> None:
        resp = "Your IBAN is GB29NWBK60161331926819 for the deposit."
        result = self.detector.run("", resp, "gpt-4", self.cfg)
        assert result.detected is True
        assert "IBAN" in result.title

    # --- CVV (needs context keyword) ---

    def test_cvv_detected(self) -> None:
        resp = "Your card verification CVV code is 123."
        result = self.detector.run("", resp, "gpt-4", self.cfg)
        assert result.detected is True
        assert result.severity == "critical"

    # --- Trade confirmation ---

    def test_trade_confirmation_detected(self) -> None:
        resp = "BOUGHT 500 shares of AAPL at $175.50"
        result = self.detector.run("", resp, "gpt-4", self.cfg)
        assert result.detected is True
        assert "Trade Confirmation" in result.title

    # --- Wire transfer ---

    def test_wire_transfer_detected(self) -> None:
        resp = "Wire reference: WT2024001234 to beneficiary account 987654321."
        result = self.detector.run("", resp, "gpt-4", self.cfg)
        assert result.detected is True
        assert result.severity == "critical"

    # --- Tax ID / EIN ---

    def test_ein_detected(self) -> None:
        resp = "The employer identification number is 12-3456789."
        result = self.detector.run("", resp, "gpt-4", self.cfg)
        assert result.detected is True
        assert "Tax ID" in result.title

    # --- MNPI indicator ---

    def test_mnpi_detected(self) -> None:
        resp = "This is material non-public information about the upcoming merger."
        result = self.detector.run("", resp, "gpt-4", self.cfg)
        assert result.detected is True
        assert result.severity == "critical"
        assert "MNPI" in result.title

    # --- Portfolio position ---

    def test_portfolio_position_detected(self) -> None:
        resp = "Client holds 1,000 shares of MSFT in their portfolio."
        result = self.detector.run("", resp, "gpt-4", self.cfg)
        assert result.detected is True

    # --- CUSIP (needs context keyword) ---

    def test_cusip_detected(self) -> None:
        resp = "The CUSIP identifier for this bond is 912828M80."
        result = self.detector.run("", resp, "gpt-4", self.cfg)
        assert result.detected is True

    # --- Clean response ---

    def test_clean_response_passes(self) -> None:
        resp = "Your application has been received. We will process it within 3 business days."
        result = self.detector.run("", resp, "gpt-4", self.cfg)
        assert result.detected is False

    # --- Disabled patterns ---

    def test_disabled_pattern_skipped(self) -> None:
        cfg: dict[str, object] = {"disabled_patterns": ["MNPI Indicator"]}
        resp = "This is material non-public information about the merger."
        result = self.detector.run("", resp, "gpt-4", cfg)
        assert "MNPI" not in (result.title or "")

    # --- Redaction ---

    def test_redacted_response_in_details(self) -> None:
        resp = "Your ABA routing number is 021000021."
        result = self.detector.run("", resp, "gpt-4", self.cfg)
        assert result.detected is True
        redacted = result.details.get("redacted_response", "")
        assert "021000021" not in redacted
