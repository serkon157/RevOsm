"""
Розрахункове ядро зворотноосмотичної установки (1- та 2-ступеневої).
Розроблено на основі математичної моделі з Google Colab та методичних вказівок ХТС.
"""

from typing import Dict, Any, List, Tuple
import pandas as pd
import numpy as np


def zmishyvach(Gr: float, Ck: float, Ci: float, Gv: float) -> Tuple[float, float]:
    """
    Змішувач свіжої вихідної води та рециклу перед першою мембраною.
    
    Параметри:
        Gr: витрата потоку рециклу, м3/год
        Ck: солевміст потоку рециклу, мг/дм3
        Ci: солевміст вихідної води, мг/дм3
        Gv: загальна витрата води на вході в мембрану, м3/год
        
    Повертає:
        Gi: необхідна витрата свіжої вихідної води, м3/год
        Cv: солевміст води на вході в мембрану після змішування, мг/дм3
    """
    Gi = Gv - Gr
    if Gv > 0:
        Cv = (Gr * Ck + Gi * Ci) / Gv
    else:
        Cv = Ci
    return Gi, Cv


def rozdiluvach(Gk: float, Xr: float) -> Tuple[float, float]:
    """
    Розділювач концентрату на рецикл та скид у каналізацію/дренаж.
    
    Параметри:
        Gk: витрата концентрату, м3/год
        Xr: частка рециклу (коефіцієнт рециркуляції), 0..1
        
    Повертає:
        Gr: витрата рециркуляційної води, м3/год
        Gs: витрата стічних вод (скид), м3/год
    """
    Gr = Gk * Xr
    Gs = Gk - Gr
    return Gr, Gs


def membrana(Gv: float, Cv: float, Xz: float, Xp: float) -> Tuple[float, float, float, float]:
    """
    Зворотноосмотична мембрана (розділення розчину під тиском).
    
    Параметри:
        Gv: витрата на вході в мембрану, м3/год
        Cv: солевміст на вході в мембрану, мг/дм3
        Xz: ступінь знесолення (селективність мембрани, Xob), 0..1
        Xp: вихід пермеату (recovery rate), 0..1
        
    Повертає:
        Gp: витрата пермеату (знесоленої води), м3/год
        Cp: солевміст пермеату, мг/дм3
        Gk: витрата концентрату (розсолу), м3/год
        Ck: солевміст концентрату, мг/дм3
    """
    Gp = Gv * Xp
    Gk = Gv - Gp
    Cp = Cv * (1.0 - Xz)
    if Gk > 0:
        Ck = (Gv * Cv - Gp * Cp) / Gk
    else:
        Ck = Cv
    return Gp, Cp, Gk, Ck


def zmish2(Gr1: float, Ck1: float, Gr2: float, Ck2: float) -> Tuple[float, float]:
    """
    Змішувач двох рециркуляційних потоків концентрату від 1-ї та 2-ї ступенів.
    
    Параметри:
        Gr1: витрата рециклу 1-ї ступені, м3/год
        Ck1: солевміст концентрату 1-ї ступені, мг/дм3
        Gr2: витрата рециклу 2-ї ступені, м3/год
        Ck2: солевміст концентрату 2-ї ступені, мг/дм3
        
    Повертає:
        Grr: сумарна витрата рециклу, м3/год
        Ckk: зважений солевміст суміші рециклів, мг/дм3
    """
    Grr = Gr1 + Gr2
    if Grr > 0:
        Ckk = (Gr1 * Ck1 + Gr2 * Ck2) / Grr
    else:
        Ckk = 0.0
    return Grr, Ckk


def calculate_single_stage(
    Ci: float = 1500.0,
    Gv: float = 100.0,
    Xz: float = 0.99,
    Xp: float = 0.20,
    Xr: float = 0.77,
    max_iter: int = 100,
    tol: float = 1e-7,
    Cv_init_factor: float = 1.2
) -> Dict[str, Any]:
    """
    Ітераційний розрахунок одноступеневої установки зворотного осмосу з рециклом.
    """
    Cv = Cv_init_factor * Ci
    history: List[Dict[str, float]] = []

    Gp, Cp, Gk, Ck = 0.0, 0.0, 0.0, 0.0
    Gr, Gs, Gi = 0.0, 0.0, 0.0

    converged = False
    iterations_run = 0

    for i in range(max_iter):
        iterations_run += 1
        Cv_prev = Cv

        Gp, Cp, Gk, Ck = membrana(Gv, Cv, Xz, Xp)
        Gr, Gs = rozdiluvach(Gk, Xr)
        Gi, Cv = zmishyvach(Gr, Ck, Ci, Gv)

        diff = abs(Cv - Cv_prev)
        history.append({
            "iteration": i + 1,
            "Cv": Cv,
            "Cp": Cp,
            "Ck": Ck,
            "diff": diff
        })

        if diff < tol and i > 2:
            converged = True
            break

    # Перевірка матеріального балансу "великого чорного ящика"
    LP = Gi * Ci                  # Прихід солей з вихідною водою
    RP = Gp * Cp + Gs * Ck        # Витрата солей (пермеат + скид)
    delta_salt = LP - RP
    rel_error_salt = (abs(delta_salt) / LP * 100) if LP > 0 else 0.0

    water_in = Gi
    water_out = Gp + Gs
    delta_water = water_in - water_out

    is_ok = abs(delta_salt) <= 0.001

    streams_df = pd.DataFrame([
        {"Потік": "Вихідна свіжа вода (Gi)", "Позначення": "Gi, Ci", "Витрата G (м³/год)": Gi, "Солевміст C (мг/дм³)": Ci, "Потік солі G·C (г/год)": Gi * Ci},
        {"Потік": "Суміш перед мембраною (Gv)", "Позначення": "Gv, Cv", "Витрата G (м³/год)": Gv, "Солевміст C (мг/дм³)": Cv, "Потік солі G·C (г/год)": Gv * Cv},
        {"Потік": "Пермеат (очищена вода, Gp)", "Позначення": "Gp, Cp", "Витрата G (м³/год)": Gp, "Солевміст C (мг/дм³)": Cp, "Потік солі G·C (г/год)": Gp * Cp},
        {"Потік": "Концентрат мембрани (Gk)", "Позначення": "Gk, Ck", "Витрата G (м³/год)": Gk, "Солевміст C (мг/дм³)": Ck, "Потік солі G·C (г/год)": Gk * Ck},
        {"Потік": "Рецикл концентрату (Gr)", "Позначення": "Gr, Ck", "Витрата G (м³/год)": Gr, "Солевміст C (мг/дм³)": Ck, "Потік солі G·C (г/год)": Gr * Ck},
        {"Потік": "Скид концентрату / дренаж (Gs)", "Позначення": "Gs, Ck", "Витрата G (м³/год)": Gs, "Солевміст C (мг/дм³)": Ck, "Потік солі G·C (г/год)": Gs * Ck},
    ])

    return {
        "scheme": "1-stage",
        "Gi": Gi, "Ci": Ci,
        "Gv": Gv, "Cv": Cv,
        "Gp": Gp, "Cp": Cp,
        "Gk": Gk, "Ck": Ck,
        "Gr": Gr, "Gs": Gs,
        "Xr": Xr, "Xp": Xp, "Xz": Xz,
        "LP": LP, "RP": RP,
        "delta_salt": delta_salt,
        "rel_error_salt": rel_error_salt,
        "delta_water": delta_water,
        "is_ok": is_ok,
        "iterations_run": iterations_run,
        "converged": converged,
        "history": pd.DataFrame(history),
        "streams_df": streams_df,
        "recovery_total": (Gp / Gi * 100.0) if Gi > 0 else 0.0,
        "desalination_degree": ((Ci - Cp) / Ci * 100.0) if Ci > 0 else 0.0
    }


def calculate_two_stage(
    Ci: float = 1500.0,
    Gv: float = 100.0,
    Xz1: float = 0.99,
    Xp1: float = 0.20,
    Xr1: float = 0.20,
    Xz2: float = 0.99,
    Xp2: float = 0.20,
    Xr2: float = 0.25,
    max_iter: int = 100,
    tol: float = 1e-7,
    Cv_init_factor: float = 1.1
) -> Dict[str, Any]:
    """
    Ітераційний розрахунок двоступеневої установки зворотного осмосу.
    """
    Cv1 = Cv_init_factor * Ci
    history: List[Dict[str, float]] = []

    Gp1, Cp1, Gk1, Ck1 = 0.0, 0.0, 0.0, 0.0
    Gp2, Cp2, Gk2, Ck2 = 0.0, 0.0, 0.0, 0.0
    Gr1, Gs1, Gr2, Gs2 = 0.0, 0.0, 0.0, 0.0
    Grr, Ckk = 0.0, 0.0
    Gii = 0.0

    converged = False
    iterations_run = 0

    for i in range(max_iter):
        iterations_run += 1
        Cv1_prev = Cv1

        # Мембрана 1
        Gp1, Cp1, Gk1, Ck1 = membrana(Gv, Cv1, Xz1, Xp1)
        # Мембрана 2 (живленням є пермеат 1-ї ступені)
        Gp2, Cp2, Gk2, Ck2 = membrana(Gp1, Cp1, Xz2, Xp2)
        # Розділювачі концентратів
        Gr1, Gs1 = rozdiluvach(Gk1, Xr1)
        Gr2, Gs2 = rozdiluvach(Gk2, Xr2)
        # Змішувач двох рециклів
        Grr, Ckk = zmish2(Gr1, Ck1, Gr2, Ck2)
        # Змішувач перед першою мембраною
        Gii, Cv1 = zmishyvach(Grr, Ckk, Ci, Gv)

        diff = abs(Cv1 - Cv1_prev)
        history.append({
            "iteration": i + 1,
            "Cv1": Cv1,
            "Cp1": Cp1,
            "Ck1": Ck1,
            "Cp2": Cp2,
            "Ck2": Ck2,
            "Ckk": Ckk,
            "diff": diff
        })

        if diff < tol and i > 2:
            converged = True
            break

    # Перевірка матеріального балансу "великого чорного ящика"
    LP = Gii * Ci                              # Прихід солей з вихідною водою
    RP = Gp2 * Cp2 + Gs1 * Ck1 + Gs2 * Ck2      # Витрата солей (пермеат 2 + скид 1 + скид 2)
    delta_salt = LP - RP
    rel_error_salt = (abs(delta_salt) / LP * 100) if LP > 0 else 0.0

    water_in = Gii
    water_out = Gp2 + Gs1 + Gs2
    delta_water = water_in - water_out

    is_ok = abs(delta_salt) <= 0.001

    total_waste = Gs1 + Gs2
    recovery_total = (Gp2 / Gii * 100.0) if Gii > 0 else 0.0
    desalination_degree = ((Ci - Cp2) / Ci * 100.0) if Ci > 0 else 0.0

    streams_df = pd.DataFrame([
        {"Потік": "Вихідна свіжа вода (Gi)", "Позначення": "Gi, Ci", "Витрата G (м³/год)": Gii, "Солевміст C (мг/дм³)": Ci, "Потік солі G·C (г/год)": Gii * Ci},
        {"Потік": "Суміш на вході в мембрану 1", "Позначення": "Gv, Cv1", "Витрата G (м³/год)": Gv, "Солевміст C (мг/дм³)": Cv1, "Потік солі G·C (г/год)": Gv * Cv1},
        {"Потік": "Пермеат 1 (вхід у ступінь 2)", "Позначення": "Gp1, Cp1", "Витрата G (м³/год)": Gp1, "Солевміст C (мг/дм³)": Cp1, "Потік солі G·C (г/год)": Gp1 * Cp1},
        {"Потік": "Концентрат мембрани 1", "Позначення": "Gk1, Ck1", "Витрата G (м³/год)": Gk1, "Солевміст C (мг/дм³)": Ck1, "Потік солі G·C (г/год)": Gk1 * Ck1},
        {"Потік": "Рецикл ступені 1", "Позначення": "Gr1, Ck1", "Витрата G (м³/год)": Gr1, "Солевміст C (мг/дм³)": Ck1, "Потік солі G·C (г/год)": Gr1 * Ck1},
        {"Потік": "Скид ступені 1", "Позначення": "Gs1, Ck1", "Витрата G (м³/год)": Gs1, "Солевміст C (мг/дм³)": Ck1, "Потік солі G·C (г/год)": Gs1 * Ck1},
        {"Потік": "Кінцевий пермеат (чиста вода)", "Позначення": "Gp2, Cp2", "Витрата G (м³/год)": Gp2, "Солевміст C (мг/дм³)": Cp2, "Потік солі G·C (г/год)": Gp2 * Cp2},
        {"Потік": "Концентрат мембрани 2", "Позначення": "Gk2, Ck2", "Витрата G (м³/год)": Gk2, "Солевміст C (мг/дм³)": Ck2, "Потік солі G·C (г/год)": Gk2 * Ck2},
        {"Потік": "Рецикл ступені 2", "Позначення": "Gr2, Ck2", "Витрата G (м³/год)": Gr2, "Солевміст C (мг/дм³)": Ck2, "Потік солі G·C (г/год)": Gr2 * Ck2},
        {"Потік": "Скид ступені 2", "Позначення": "Gs2, Ck2", "Витрата G (м³/год)": Gs2, "Солевміст C (мг/дм³)": Ck2, "Потік солі G·C (г/год)": Gs2 * Ck2},
        {"Потік": "Об'єднаний рецикл", "Позначення": "Grr, Ckk", "Витрата G (м³/год)": Grr, "Солевміст C (мг/дм³)": Ckk, "Потік солі G·C (г/год)": Grr * Ckk},
    ])

    return {
        "scheme": "2-stage",
        "Gii": Gii, "Ci": Ci,
        "Gv": Gv, "Cv1": Cv1,
        "Gp1": Gp1, "Cp1": Cp1,
        "Gk1": Gk1, "Ck1": Ck1,
        "Gp2": Gp2, "Cp2": Cp2,
        "Gk2": Gk2, "Ck2": Ck2,
        "Gr1": Gr1, "Gs1": Gs1,
        "Gr2": Gr2, "Gs2": Gs2,
        "Grr": Grr, "Ckk": Ckk,
        "Xr1": Xr1, "Xr2": Xr2,
        "Xp1": Xp1, "Xp2": Xp2,
        "Xz1": Xz1, "Xz2": Xz2,
        "LP": LP, "RP": RP,
        "delta_salt": delta_salt,
        "rel_error_salt": rel_error_salt,
        "delta_water": delta_water,
        "is_ok": is_ok,
        "total_waste": total_waste,
        "recovery_total": recovery_total,
        "desalination_degree": desalination_degree,
        "iterations_run": iterations_run,
        "converged": converged,
        "history": pd.DataFrame(history),
        "streams_df": streams_df
    }


def find_optimal_xr2_for_cv_target(
    target_Cv1: float,
    Ci: float = 1500.0,
    Gv: float = 100.0,
    Xz1: float = 0.99,
    Xp1: float = 0.20,
    Xr1: float = 0.20,
    Xz2: float = 0.99,
    Xp2: float = 0.20,
    tol: float = 0.01,
    max_steps: int = 50
) -> Tuple[float, Dict[str, Any]]:
    """
    Метод підбору рециклу другої ступені Xr2 (Goal Seek),
    за якого солевміст води на вході у мембрану першого ступеня Cv1 наближається до target_Cv1 (наприклад, Ci).
    """
    low = 0.0
    high = 0.999
    best_res = calculate_two_stage(Ci, Gv, Xz1, Xp1, Xr1, Xz2, Xp2, Xr2=0.0)

    res_low = calculate_two_stage(Ci, Gv, Xz1, Xp1, Xr1, Xz2, Xp2, Xr2=low)
    res_high = calculate_two_stage(Ci, Gv, Xz1, Xp1, Xr1, Xz2, Xp2, Xr2=high)

    f_low = res_low["Cv1"] - target_Cv1
    f_high = res_high["Cv1"] - target_Cv1

    if f_low * f_high > 0:
        grid = np.linspace(0.0, 0.99, 100)
        best_diff = float("inf")
        best_xr2 = 0.0
        for x in grid:
            res = calculate_two_stage(Ci, Gv, Xz1, Xp1, Xr1, Xz2, Xp2, Xr2=x)
            diff = abs(res["Cv1"] - target_Cv1)
            if diff < best_diff:
                best_diff = diff
                best_xr2 = x
                best_res = res
        return best_xr2, best_res

    for _ in range(max_steps):
        mid = (low + high) / 2.0
        res_mid = calculate_two_stage(Ci, Gv, Xz1, Xp1, Xr1, Xz2, Xp2, Xr2=mid)
        f_mid = res_mid["Cv1"] - target_Cv1

        if abs(f_mid) < tol:
            return mid, res_mid

        if f_low * f_mid < 0:
            high = mid
            f_high = f_mid
        else:
            low = mid
            f_low = f_mid

    best_res = calculate_two_stage(Ci, Gv, Xz1, Xp1, Xr1, Xz2, Xp2, Xr2=(low + high) / 2.0)
    return (low + high) / 2.0, best_res


def find_optimal_xr_single_stage(
    target_Cv: float,
    Ci: float = 1500.0,
    Gv: float = 100.0,
    Xz: float = 0.99,
    Xp: float = 0.20,
    tol: float = 0.01,
    max_steps: int = 50
) -> Tuple[float, Dict[str, Any]]:
    """
    Метод підбору рециклу Xr для одноступеневої установки,
    за якого солевміст води на вході у мембрану Cv наближається до target_Cv.
    """
    low = 0.0
    high = 0.95
    res_low = calculate_single_stage(Ci, Gv, Xz, Xp, Xr=low)
    res_high = calculate_single_stage(Ci, Gv, Xz, Xp, Xr=high)

    f_low = res_low["Cv"] - target_Cv
    f_high = res_high["Cv"] - target_Cv

    if f_low * f_high > 0:
        grid = np.linspace(0.0, 0.95, 100)
        best_diff = float("inf")
        best_xr = 0.0
        best_res = res_low
        for x in grid:
            res = calculate_single_stage(Ci, Gv, Xz, Xp, Xr=x)
            diff = abs(res["Cv"] - target_Cv)
            if diff < best_diff:
                best_diff = diff
                best_xr = x
                best_res = res
        return best_xr, best_res

    for _ in range(max_steps):
        mid = (low + high) / 2.0
        res_mid = calculate_single_stage(Ci, Gv, Xz, Xp, Xr=mid)
        f_mid = res_mid["Cv"] - target_Cv

        if abs(f_mid) < tol:
            return mid, res_mid

        if f_low * f_mid < 0:
            high = mid
            f_high = f_mid
        else:
            low = mid
            f_low = f_mid

    best_res = calculate_single_stage(Ci, Gv, Xz, Xp, Xr=(low + high) / 2.0)
    return (low + high) / 2.0, best_res



def get_dot_single_stage(res: Dict[str, Any]) -> str:
    """Генерація вихідного коду Graphviz DOT для 1-ступеневої схеми."""
    return f"""digraph SingleStageRO {{
    rankdir=LR;
    bgcolor="transparent";
    node [fontname="Segoe UI, Arial, sans-serif", fontsize=11, style="filled,rounded", shape=box, penwidth=1.5];
    edge [fontname="Segoe UI, Arial, sans-serif", fontsize=10, penwidth=1.8, color="#37474F"];

    // Вузли
    feed   [label="Вихідна вода\\nGi = {res['Gi']:.2f} м³/год\\nCi = {res['Ci']:.1f} мг/дм³", fillcolor="#E1F5FE", color="#0288D1", shape=ellipse];
    mix    [label="Змішувач 1\\n(Feed Mixer)", fillcolor="#FFF9C4", color="#FBC02D"];
    membr  [label="Мембрана 1\\n(RO Stage 1)\\nXp={res['Xp']:.2f}, Xz={res['Xz']:.3f}", fillcolor="#C8E6C9", color="#388E3C"];
    sep    [label="Розділювач 1\\n(Splitter)\\nXr = {res['Xr']:.2f}", fillcolor="#FFE0B2", color="#F57C00"];
    perm   [label="ОЧИЩЕНА ВОДА\\n(Пермеат Gp)\\n{res['Gp']:.2f} м³/год\\n{res['Cp']:.2f} мг/дм³", fillcolor="#B2EBF2", color="#00838F", shape=doublecircle];
    drain  [label="СКИД РОЗСОЛУ\\n(Дренаж Gs)\\n{res['Gs']:.2f} м³/год\\n{res['Ck']:.1f} мг/дм³", fillcolor="#FFCDD2", color="#C62828", shape=ellipse];

    // Зв'язки
    feed -> mix   [label="Gi={res['Gi']:.2f}\\nCi={res['Ci']:.0f}"];
    mix -> membr  [label="Gv={res['Gv']:.2f}\\nCv={res['Cv']:.1f}", color="#1E88E5"];
    membr -> perm [label="Gp={res['Gp']:.2f}\\nCp={res['Cp']:.2f}", color="#00897B"];
    membr -> sep  [label="Gk={res['Gk']:.2f}\\nCk={res['Ck']:.1f}", color="#E53935"];
    sep -> drain  [label="Gs={res['Gs']:.2f}\\nCk={res['Ck']:.1f}", color="#C62828"];
    sep -> mix    [label="Рецикл Gr={res['Gr']:.2f}\\nCk={res['Ck']:.1f}", style=dashed, color="#FB8C00", constraint=false];
}}"""


def get_dot_two_stage(res: Dict[str, Any]) -> str:
    """Генерація вихідного коду Graphviz DOT для 2-ступеневої схеми."""
    return f"""digraph TwoStageRO {{
    rankdir=LR;
    bgcolor="transparent";
    node [fontname="Segoe UI, Arial, sans-serif", fontsize=11, style="filled,rounded", shape=box, penwidth=1.5];
    edge [fontname="Segoe UI, Arial, sans-serif", fontsize=10, penwidth=1.8, color="#37474F"];

    // Вузли
    feed   [label="Вихідна свіжа вода\\nGi = {res['Gii']:.2f} м³/год\\nCi = {res['Ci']:.1f} мг/дм³", fillcolor="#E1F5FE", color="#0288D1", shape=ellipse];
    mix1   [label="Змішувач 1\\n(Перед М1)", fillcolor="#FFF9C4", color="#FBC02D"];
    m1     [label="Мембрана 1\\n(Ступінь 1)\\nXp1={res['Xp1']:.2f}, Xz1={res['Xz1']:.3f}", fillcolor="#C8E6C9", color="#388E3C"];
    sep1   [label="Розділювач 1\\n(Xr1 = {res['Xr1']:.2f})", fillcolor="#FFE0B2", color="#F57C00"];
    drain1 [label="Скид 1 (Gs1)\\n{res['Gs1']:.2f} м³/год\\n{res['Ck1']:.1f} мг/дм³", fillcolor="#FFCDD2", color="#C62828", shape=ellipse];

    m2     [label="Мембрана 2\\n(Ступінь 2)\\nXp2={res['Xp2']:.2f}, Xz2={res['Xz2']:.3f}", fillcolor="#C8E6C9", color="#388E3C"];
    sep2   [label="Розділювач 2\\n(Xr2 = {res['Xr2']:.2f})", fillcolor="#FFE0B2", color="#F57C00"];
    drain2 [label="Скид 2 (Gs2)\\n{res['Gs2']:.2f} м³/год\\n{res['Ck2']:.1f} мг/дм³", fillcolor="#FFCDD2", color="#C62828", shape=ellipse];

    mix2   [label="Змішувач 2\\n(Рецикли)", fillcolor="#FFF9C4", color="#FBC02D"];
    perm2  [label="КІНЦЕВИЙ ПЕРМЕАТ\\nGp2 = {res['Gp2']:.2f} м³/год\\nCp2 = {res['Cp2']:.3f} мг/дм³", fillcolor="#B2EBF2", color="#00838F", shape=doublecircle];

    // Потоки
    feed -> mix1  [label="Gi={res['Gii']:.2f}\\nCi={res['Ci']:.0f}"];
    mix1 -> m1    [label="Gv={res['Gv']:.2f}\\nCv1={res['Cv1']:.1f}", color="#1E88E5"];
    m1 -> sep1    [label="Концентрат 1\\nGk1={res['Gk1']:.2f}\\nCk1={res['Ck1']:.1f}", color="#E53935"];
    m1 -> m2      [label="Пермеат 1\\nGp1={res['Gp1']:.2f}\\nCp1={res['Cp1']:.2f}", color="#00897B"];

    sep1 -> drain1 [label="Gs1={res['Gs1']:.2f}", color="#C62828"];
    sep1 -> mix2   [label="Gr1={res['Gr1']:.2f}", color="#FB8C00"];

    m2 -> perm2   [label="Gp2={res['Gp2']:.2f}\\nCp2={res['Cp2']:.3f}", color="#00897B"];
    m2 -> sep2    [label="Концентрат 2\\nGk2={res['Gk2']:.2f}\\nCk2={res['Ck2']:.1f}", color="#E53935"];

    sep2 -> drain2 [label="Gs2={res['Gs2']:.2f}", color="#C62828"];
    sep2 -> mix2   [label="Gr2={res['Gr2']:.2f}", color="#FB8C00"];

    mix2 -> mix1  [label="Сумарний рецикл\\nGrr={res['Grr']:.2f} м³/год\\nCkk={res['Ckk']:.1f} мг/дм³", style=dashed, color="#3949AB", constraint=false];
}}"""


def compute_recycle_sensitivity(
    Ci: float, Gv: float, Xz1: float, Xp1: float, Xr1: float,
    Xz2: float, Xp2: float, Xr2: float, vary_param: str = "Xr2"
) -> pd.DataFrame:
    """Розрахунок чутливості до коефіцієнта рециклу (Xr1 або Xr2)."""
    r_values = np.linspace(0.0, 0.90, 30)
    data = []

    for r in r_values:
        cur_xr1 = r if vary_param == "Xr1" else Xr1
        cur_xr2 = r if vary_param == "Xr2" else Xr2

        res = calculate_two_stage(
            Ci=Ci, Gv=Gv,
            Xz1=Xz1, Xp1=Xp1, Xr1=cur_xr1,
            Xz2=Xz2, Xp2=Xp2, Xr2=cur_xr2
        )
        data.append({
            "Recycle_Ratio": r,
            "Cv1": res["Cv1"],
            "Cp2": res["Cp2"],
            "Ck1": res["Ck1"],
            "Ck2": res["Ck2"],
            "Gii": res["Gii"],
            "Gp2": res["Gp2"],
            "Total_Waste": res["total_waste"],
            "Recovery_Pct": res["recovery_total"]
        })

    return pd.DataFrame(data)
