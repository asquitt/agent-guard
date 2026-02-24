"""Adversarial tests for ComplianceDetector.

Each test targets a specific bypass technique involving subtle regulatory
violations wrapped in legitimate language, edge-case advice, or
multi-jurisdiction conflicts.
"""

from __future__ import annotations

from unittest.mock import patch

from app.services.detection.compliance import ComplianceDetector


class TestComplianceAdversarial:
    """Adversarial attacks against the compliance detector."""

    detector = ComplianceDetector()
    cfg: dict[str, object] = {"llm_verify": False}

    # ------------------------------------------------------------------
    # 1. Subtle regulatory violations in legitimate language
    # ------------------------------------------------------------------

    def test_sox_material_weakness_hidden(self) -> None:
        """Violation: SOX material weakness reference wrapped in business language."""
        response = (
            "The quarterly review identified a material weakness in our "
            "internal controls over financial reporting."
        )
        result = self.detector.run("", response, "gpt-4", self.cfg)
        assert result.detected is True, "SOX material weakness not detected"

    def test_sox_disclosure_in_narrative(self) -> None:
        """Violation: SOX disclosure controls reference in narrative text."""
        response = (
            "Management has updated the disclosure controls procedures "
            "following the audit committee's recommendations."
        )
        result = self.detector.run("", response, "gpt-4", self.cfg)
        assert result.detected is True, "SOX disclosure controls not detected"

    # ------------------------------------------------------------------
    # 2. PCI-DSS violations
    # ------------------------------------------------------------------

    def test_pci_cardholder_data_exposure(self) -> None:
        """Violation: PCI-DSS cardholder data discussion."""
        response = (
            "The cardholder data environment needs to be segmented "
            "from the rest of the network for PCI compliance."
        )
        result = self.detector.run("", response, "gpt-4", self.cfg)
        assert result.detected is True, "PCI cardholder data not detected"

    def test_pci_cvv_storage_discussion(self) -> None:
        """Violation: Discussion about CVV storage practices."""
        response = (
            "We should review our card verification process to ensure "
            "CVV data is not being stored after authorization."
        )
        result = self.detector.run("", response, "gpt-4", self.cfg)
        assert result.detected is True, "PCI CVV discussion not detected"

    # ------------------------------------------------------------------
    # 3. FFIEC fair lending violations
    # ------------------------------------------------------------------

    def test_ffiec_disparate_impact(self) -> None:
        """Violation: FFIEC disparate impact in lending."""
        response = (
            "The analysis shows a potential disparate impact in our "
            "lending criteria that may affect certain demographics."
        )
        result = self.detector.run("", response, "gpt-4", self.cfg)
        assert result.detected is True, "FFIEC disparate impact not detected"

    def test_ffiec_redlining_reference(self) -> None:
        """Violation: Reference to redlining practices."""
        response = (
            "Historical redlining patterns still affect property values "
            "in certain neighborhoods and our lending decisions."
        )
        result = self.detector.run("", response, "gpt-4", self.cfg)
        assert result.detected is True, "FFIEC redlining not detected"

    # ------------------------------------------------------------------
    # 4. Edge-case financial advice
    # ------------------------------------------------------------------

    def test_implied_investment_advice(self) -> None:
        """Edge case: Implied investment advice that could violate regulations."""
        response = (
            "Based on the risk assessment and risk management system, "
            "the portfolio should be rebalanced."
        )
        result = self.detector.run("", response, "gpt-4", self.cfg)
        assert result.detected is True, "Risk management system reference not detected"

    # ------------------------------------------------------------------
    # 5. Multi-jurisdiction conflicts
    # ------------------------------------------------------------------

    def test_eu_ai_act_transparency(self) -> None:
        """EU AI Act: AI transparency requirement reference."""
        response = (
            "The AI transparency requirements under the EU AI Act "
            "mandate clear disclosure of AI-generated content."
        )
        result = self.detector.run("", response, "gpt-4", self.cfg)
        assert result.detected is True, "EU AI Act transparency not detected"

    def test_dora_operational_resilience(self) -> None:
        """DORA: Operational resilience requirement."""
        response = (
            "The operational resilience framework must be tested "
            "annually per DORA requirements."
        )
        result = self.detector.run("", response, "gpt-4", self.cfg)
        assert result.detected is True, "DORA operational resilience not detected"

    # ------------------------------------------------------------------
    # 6. NYDFS cybersecurity requirements
    # ------------------------------------------------------------------

    def test_nydfs_access_control(self) -> None:
        """NYDFS-500: Access control/privilege reference."""
        response = (
            "Implement least privilege access control for all users "
            "accessing the financial systems."
        )
        result = self.detector.run("", response, "gpt-4", self.cfg)
        assert result.detected is True, "NYDFS access control not detected"

    def test_nydfs_security_training(self) -> None:
        """NYDFS-500: Security training requirement."""
        response = (
            "All employees must complete annual security training and "
            "security awareness programs per regulation."
        )
        result = self.detector.run("", response, "gpt-4", self.cfg)
        assert result.detected is True, "NYDFS security training not detected"

    # ------------------------------------------------------------------
    # 7. Multiple framework violations in one response
    # ------------------------------------------------------------------

    def test_multi_framework_violation(self) -> None:
        """Response triggers multiple regulatory frameworks."""
        response = (
            "The internal controls review revealed that cardholder data "
            "protection needs improvement, and our cybersecurity program "
            "must be updated to address new threats."
        )
        result = self.detector.run("", response, "gpt-4", self.cfg)
        assert result.detected is True, "Multi-framework violation not detected"
        hits = result.details.get("keyword_hits", {})
        assert len(hits) >= 2, "Should detect violations across multiple frameworks"

    # ------------------------------------------------------------------
    # 8. Framework-specific configuration
    # ------------------------------------------------------------------

    def test_frameworks_config_filter(self) -> None:
        """Only configured frameworks should be checked."""
        cfg: dict[str, object] = {"llm_verify": False, "frameworks": ["SOX"]}
        response = "The cardholder data environment needs segmentation."
        result = self.detector.run("", response, "gpt-4", cfg)
        # PCI keyword should NOT trigger since only SOX is enabled
        assert result.detected is False, "Non-configured framework triggered detection"

    # ------------------------------------------------------------------
    # 9. Clean response (no false positives)
    # ------------------------------------------------------------------

    def test_clean_financial_discussion(self) -> None:
        """Clean financial discussion without compliance keywords."""
        response = (
            "The market showed strong performance in Q4 with major "
            "indices reaching new highs. Trading volume was elevated."
        )
        result = self.detector.run("", response, "gpt-4", self.cfg)
        assert result.detected is False, "Clean response triggered false positive"

    # ------------------------------------------------------------------
    # 10. BSA/AML compliance
    # ------------------------------------------------------------------

    def test_bsa_aml_reference(self) -> None:
        """BSA/AML: Anti-money laundering compliance reference."""
        response = (
            "The anti-money laundering screening must be completed "
            "before onboarding any new institutional client."
        )
        result = self.detector.run("", response, "gpt-4", self.cfg)
        assert result.detected is True, "BSA/AML reference not detected"

    # ------------------------------------------------------------------
    # 11. DORA ICT testing
    # ------------------------------------------------------------------

    def test_dora_penetration_testing(self) -> None:
        """DORA: Penetration testing requirement."""
        response = (
            "The annual penetration test results show improvement "
            "in our ICT infrastructure security posture."
        )
        result = self.detector.run("", response, "gpt-4", self.cfg)
        assert result.detected is True, "DORA penetration test not detected"
