import unittest

from app.bot.handlers.diagnostics import _detect_stop_level, _resolve_goal_with_contradictions


class DiagnosticsSafetyTest(unittest.TestCase):
    def test_underweight_fat_loss_resolves_to_maintenance(self):
        profile = {"goal": "Похудеть", "age": 28, "sex": "male"}
        payload = {"bmi": 17.8, "whtr": 0.45}
        resolved, _, notes = _resolve_goal_with_contradictions(profile, payload)
        self.assertEqual(resolved, "maintenance")
        self.assertTrue(notes)

    def test_muscle_gain_high_risk_resolves_to_recomposition(self):
        profile = {"goal": "Набрать мышечную массу", "age": 34, "sex": "male"}
        payload = {"bmi": 31.0, "whtr": 0.62}
        resolved, _, _ = _resolve_goal_with_contradictions(profile, payload)
        self.assertEqual(resolved, "recomposition")

    def test_age_under_18_consultation_route(self):
        profile = {"goal": "Похудеть", "age": 16, "sex": "female"}
        payload = {"bmi": 22.0, "whtr": 0.45}
        resolved, _, _ = _resolve_goal_with_contradictions(profile, payload)
        self.assertEqual(resolved, "consultation_only")

    def test_pressure_hard_stop(self):
        profile = {"pressure_text": "180/120", "pregnancy_status": "Нет", "health_notes": "—", "sex": "male"}
        payload = {"whtr": 0.45, "whr": 0.8}
        stop_level, _ = _detect_stop_level(profile, payload)
        self.assertEqual(stop_level, "hard_stop")


if __name__ == "__main__":
    unittest.main()
