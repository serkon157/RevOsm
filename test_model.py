"""
Автоматичні тести для розрахункового ядра зворотноосмотичної системи (model.py).
"""

import unittest
import model


class TestRevOsmModel(unittest.TestCase):

    def test_single_stage_balance(self):
        # Параметри з Google Colab
        res = model.calculate_single_stage(
            Ci=1500.0, Gv=100.0, Xz=0.99, Xp=0.20, Xr=0.77
        )
        # Перевірка сходу матеріального балансу по воді
        self.assertAlmostEqual(res["delta_water"], 0.0, places=5)
        # Перевірка матеріального балансу по солях
        self.assertLess(abs(res["delta_salt"]), 0.001)
        self.assertTrue(res["is_ok"])
        # Перевірка збіжності
        self.assertTrue(res["converged"])
        # Перевірка витрат
        self.assertAlmostEqual(res["Gp"], 20.0, places=3)
        self.assertAlmostEqual(res["Gk"], 80.0, places=3)
        self.assertAlmostEqual(res["Gi"], 38.4, places=3)
        self.assertAlmostEqual(res["Gs"], 18.4, places=3)

    def test_two_stage_balance(self):
        # Параметри з Google Colab
        res = model.calculate_two_stage(
            Ci=1500.0, Gv=100.0,
            Xz1=0.99, Xp1=0.20, Xr1=0.20,
            Xz2=0.99, Xp2=0.20, Xr2=0.25
        )
        # Перевірка сходу матеріального балансу по воді (Gii == Gp2 + Gs1 + Gs2)
        self.assertAlmostEqual(res["delta_water"], 0.0, places=5)
        # Перевірка балансу по солях (|LP - RP| <= 0.001)
        self.assertLess(abs(res["delta_salt"]), 0.001)
        self.assertTrue(res["is_ok"])
        self.assertTrue(res["converged"])
        # Перевірка витрат потоків
        self.assertAlmostEqual(res["Gp1"], 20.0, places=3)
        self.assertAlmostEqual(res["Gp2"], 4.0, places=3)
        self.assertAlmostEqual(res["Gk1"], 80.0, places=3)
        self.assertAlmostEqual(res["Gk2"], 16.0, places=3)
        self.assertAlmostEqual(res["Gr1"], 16.0, places=3)
        self.assertAlmostEqual(res["Gr2"], 4.0, places=3)
        self.assertAlmostEqual(res["Grr"], 20.0, places=3)
        self.assertAlmostEqual(res["Gii"], 80.0, places=3)
        self.assertAlmostEqual(res["Gs1"], 64.0, places=3)
        self.assertAlmostEqual(res["Gs2"], 12.0, places=3)
        # Перевірка високої якості кінцевого пермеату
        self.assertLess(res["Cp2"], 1.0)  # Солевміст пермеату < 1 мг/дм³

    def test_goal_seek(self):
        target = 1500.0
        opt_xr2, res = model.find_optimal_xr2_for_cv_target(
            target_Cv1=target, Ci=1500.0, Gv=100.0
        )
        self.assertGreater(opt_xr2, 0.0)
        self.assertLess(opt_xr2, 1.0)
        self.assertAlmostEqual(res["Cv1"], target, delta=0.05)

    def test_goal_seek_single_stage(self):
        target = 2000.0
        opt_xr, res = model.find_optimal_xr_single_stage(
            target_Cv=target, Ci=1500.0, Gv=100.0, Xz=0.99, Xp=0.20
        )
        self.assertGreater(opt_xr, 0.0)
        self.assertLess(opt_xr, 1.0)
        self.assertAlmostEqual(res["Cv"], target, delta=1.0)


    def test_dot_generation(self):
        res1 = model.calculate_single_stage()
        dot1 = model.get_dot_single_stage(res1)
        self.assertIn("digraph", dot1)
        self.assertIn("SingleStageRO", dot1)

        res2 = model.calculate_two_stage()
        dot2 = model.get_dot_two_stage(res2)
        self.assertIn("digraph", dot2)
        self.assertIn("TwoStageRO", dot2)

    def test_sensitivity(self):
        df = model.compute_recycle_sensitivity(
            Ci=1500.0, Gv=100.0,
            Xz1=0.99, Xp1=0.2, Xr1=0.2,
            Xz2=0.99, Xp2=0.2, Xr2=0.25,
            vary_param="Xr2"
        )
        self.assertEqual(len(df), 30)
        self.assertIn("Cv1", df.columns)
        self.assertIn("Cp2", df.columns)


if __name__ == "__main__":
    unittest.main()
