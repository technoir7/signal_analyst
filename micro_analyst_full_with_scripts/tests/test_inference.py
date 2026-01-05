import unittest
from core.inference import InferenceEngine, SignalInference
from utils.llm_client import LLMClient

class TestInterpretiveInference(unittest.TestCase):
    
    def setUp(self):
        self.engine = InferenceEngine()
        self.client = LLMClient()  # Base deterministic client

    def test_report_renders_with_no_signals(self):
        """
        Req 1: Empty Input -> Non-Empty Report.
        No "Not available" messages allowed.
        """
        # Given: All collectors return None or empty/error
        empty_profile = {
            "web": {"error": "Timeout"},
            "seo": {"error": "Timeout"},
            "tech_stack": {"error": "Timeout"},
            "reviews": {"error": "Timeout"},
            "social": {"error": "Timeout"},
            "hiring": {"error": "Timeout"},
            "ads": {"error": "Timeout"}
        }

        # When
        inferred = self.engine.infer(empty_profile)
        inferred_dict = inferred.model_dump()
        report = self.client._build_sectioned_report(inferred_dict, "TestCorp")

        # Assert
        self.assertTrue(report, "Report should not be empty")
        
        forbidden_phrases = ["Not available", "not available", "No data found"]
        for phrase in forbidden_phrases:
            self.assertNotIn(phrase, report, f"Report contained forbidden phrase: '{phrase}'")
        
        # Check for mandatory sections
        self.assertIn("## 1. Web Presence", report)
        self.assertIn("## 8. Strategic Recommendations", report)
        self.assertTrue(len(inferred.strategic_posture) > 50, "Strategic Posture too short")

    def test_absence_generates_plausible_inference(self):
        """
        Req 2: Absence -> Interpreted Signal.
        """
        # Given
        profile = {
            "reviews": {"summary": None, "error": None},  # Explicitly absent
            "ads": {"platforms": [], "error": None},
            "social": {"twitter": None, "linkedin": None, "error": None}
        }
        
        # When
        inferred = self.engine.infer(profile)
        
        # Assert - Reviews
        self.assertEqual(inferred.reviews.data_status, "absent")
        self.assertIn("relationship", inferred.reviews.strategic_implication.lower()) # "Relationship-driven" logic
        
        # Assert - Ads
        self.assertEqual(inferred.ads.data_status, "absent") 
        self.assertIn("organic", inferred.ads.strategic_implication.lower()) # "Organic Growth" logic
        
        # Assert - Social
        self.assertEqual(inferred.social.data_status, "absent")
        self.assertIn("quiet professional", inferred.social.strategic_implication.lower())

    def test_partial_data_produces_mixed_inference(self):
        """
        Req 3: Presence + Absence -> Mixed Inference.
        """
        # Given
        profile = {
            "web": {"meta": {"title": "Real Corp"}}, # Present
            "seo": {"meta_issues": ["Missing H1"]},  # Partial/Issues
            "tech_stack": {"error": "Access Denied"} # Absent
        }
        
        # When
        inferred = self.engine.infer(profile)
        
        # Assert
        self.assertEqual(inferred.web.data_status, "present")
        self.assertEqual(inferred.seo.data_status, "partial")
        self.assertEqual(inferred.tech_stack.data_status, "absent")
        
        # Posture should reflect mixed bag?
        # The logic combines them.
        # SEO implication: "...friction suggests marketing execution lags..."
        self.assertIn("friction", inferred.seo.strategic_implication.lower()) # SEO has issues

    def test_no_hallucinated_facts(self):
        """
        Req 4: No Fabricated Facts Guarantee.
        """
        # Given: Completely empty input
        profile = {}
        
        # When
        inferred = self.engine.infer(profile)
        report = self.client._build_sectioned_report(inferred.model_dump(), "TestCorp")
        
        # Assert
        hallucinations = ["Salesforce", "HubSpot", "$10M", "100 employees"]
        for h in hallucinations:
            self.assertNotIn(h, report, "Report hallucinated a concrete fact")
            
        # Check for epistemic qualifiers
        qualifiers = ["suggests", "likely", "indicates", "implies"]
        has_qualifier = any(q in report.lower() for q in qualifiers)
        self.assertTrue(has_qualifier, "Report lacks epistemic qualifiers (suggests/likely)")

    def test_strategic_posture_is_mandatory(self):
        """
        Req 5: Strategic Posture Summary Enforcement.
        """
        # Given
        profile = {} 
        
        # When
        inferred = self.engine.infer(profile)
        
        # Assert
        self.assertIsNotNone(inferred.strategic_posture)
        self.assertNotEqual(inferred.strategic_posture, "")
        self.assertIn("The target exhibits", inferred.strategic_posture)

if __name__ == "__main__":
    unittest.main()
