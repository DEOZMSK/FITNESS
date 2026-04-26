import unittest

from app.calculators.body_metrics import whr_interpretation, waist_to_height_interpretation
from app.calculators.calories import bmr_mifflin_st_jeor


class MetricsAndCaloriesTest(unittest.TestCase):
    def test_bmr_mifflin_male(self):
        value = bmr_mifflin_st_jeor(weight_kg=80, height_cm=180, age=30, sex="male")
        self.assertAlmostEqual(value, 1780.0, places=2)

    def test_bmr_mifflin_female(self):
        value = bmr_mifflin_st_jeor(weight_kg=65, height_cm=170, age=30, sex="female")
        self.assertAlmostEqual(value, 1401.5, places=2)

    def test_whr_boundaries(self):
        self.assertIn("пограничного", whr_interpretation(0.9, "male").lower())
        self.assertIn("пограничного", whr_interpretation(0.85, "female").lower())

    def test_whtr_boundaries(self):
        self.assertEqual(waist_to_height_interpretation(0.49), "Нет повышенного риска")
        self.assertEqual(waist_to_height_interpretation(0.5), "Повышенный риск")
        self.assertEqual(waist_to_height_interpretation(0.6), "Высокий риск")


if __name__ == "__main__":
    unittest.main()
