"""
Веб-додаток на Streamlit для розрахунку матеріальних балансів
одно- та двоступеневих зворотноосмотичних установок (RevOsm).
Базується на розрахунках з Google Colab та методичних вказівках ХТС.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import model

# 1. Налаштування сторінки
st.set_page_config(
    page_title="RevOsm - Розрахунок ЗОУ",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Кастомні стилі (CSS)
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #0D47A1;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.1rem;
        color: #455A64;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #f8fafd 0%, #e8f0fe 100%);
        border: 1px solid #d0e1fd;
        border-radius: 10px;
        padding: 15px;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.04);
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1565C0;
    }
    .metric-label {
        font-size: 0.88rem;
        color: #546E7A;
        font-weight: 500;
    }
    .badge-ok {
        background-color: #E8F5E9;
        color: #2E7D32;
        border: 1px solid #A5D6A7;
        padding: 8px 14px;
        border-radius: 8px;
        font-weight: 600;
        display: inline-block;
    }
    .badge-warn {
        background-color: #FFF3E0;
        color: #E65100;
        border: 1px solid #FFCC80;
        padding: 8px 14px;
        border-radius: 8px;
        font-weight: 600;
        display: inline-block;
    }
</style>
""", unsafe_allow_html=True)

# 3. Бічна панель: налаштування та вхідні дані
st.sidebar.image("https://img.icons8.com/fluency/96/water.png", width=64)
st.sidebar.title("Параметри установки")

# Вибір технологічної схеми
scheme_choice = st.sidebar.radio(
    "Технологічна схема:",
    ["🌀 Двоступенева установка (2-Stage)", "💧 Одноступенева установка (1-Stage)"],
    index=0
)
is_two_stage = "Двоступенева" in scheme_choice

# Пресети вихідних даних
preset = st.sidebar.selectbox(
    "Пресети параметрів:",
    ["Google Colab (Ci=1500, Gv=100, Xp=0.2)", "Методичка ХТС (Xp=0.25, Xr1=0.2, Xr2=0.25)", "Користувацькі значення"]
)

# Значення за замовчуванням залежно від пресету
if preset == "Google Colab (Ci=1500, Gv=100, Xp=0.2)":
    default_Ci = 1500.0
    default_Gv = 100.0
    default_Xp1 = 0.20
    default_Xz1 = 0.990
    default_Xr1 = 0.20 if is_two_stage else 0.77
    default_Xp2 = 0.20
    default_Xz2 = 0.990
    default_Xr2 = 0.25
elif preset == "Методичка ХТС (Xp=0.25, Xr1=0.2, Xr2=0.25)":
    default_Ci = 1500.0
    default_Gv = 100.0
    default_Xp1 = 0.25
    default_Xz1 = 0.990
    default_Xr1 = 0.20
    default_Xp2 = 0.25
    default_Xz2 = 0.990
    default_Xr2 = 0.25
else:
    default_Ci = 1500.0
    default_Gv = 100.0
    default_Xp1 = 0.20
    default_Xz1 = 0.990
    default_Xr1 = 0.20 if is_two_stage else 0.50
    default_Xp2 = 0.20
    default_Xz2 = 0.990
    default_Xr2 = 0.25

# Базові значення для забезпечення безпеки доступу до змінних
Xp1 = default_Xp1
Xz1 = default_Xz1
Xr1 = default_Xr1
Xp2 = default_Xp2
Xz2 = default_Xz2
Xr2 = default_Xr2
Xp = default_Xp1
Xz = default_Xz1
Xr = default_Xr1

with st.sidebar.expander("🧪 Параметри вихідної води", expanded=True):

    Ci = st.number_input(
        "Солевміст вихідної води Ci (мг/дм³)",
        min_value=10.0, max_value=50000.0,
        value=default_Ci, step=50.0,
        help="Загальний солевміст (TDS) сирої води на вході в установку"
    )
    Gv = st.number_input(
        "Витрата на вході в 1-у мембрану Gv (м³/год)",
        min_value=0.1, max_value=10000.0,
        value=default_Gv, step=10.0,
        help="Загальна продуктивність першої мембрани за подачею (включаючи рецикли)"
    )

if is_two_stage:
    with st.sidebar.expander("⚙️ Ступінь 1 (Мембрана 1 + Розділювач 1)", expanded=True):
        Xp1 = st.slider(
            "Вихід пермеату Xp1 (recovery)",
            min_value=0.05, max_value=0.60,
            value=default_Xp1, step=0.01,
            help="Частка пермеату від подачі на мембрану 1: Gp1 = Gv * Xp1"
        )
        Xz1 = st.slider(
            "Ступінь знесолення Xz1 (селективність)",
            min_value=0.800, max_value=0.999,
            value=default_Xz1, step=0.001, format="%.3f",
            help="Селективність 1-ї мембрани: Cp1 = Cv1 * (1 - Xz1)"
        )
        Xr1 = st.slider(
            "Коефіцієнт рециклу Xr1",
            min_value=0.00, max_value=0.95,
            value=default_Xr1, step=0.01,
            help="Частка концентрату ступеня 1, що повертається у рецикл: Gr1 = Gk1 * Xr1"
        )

    with st.sidebar.expander("⚙️ Ступінь 2 (Мембрана 2 + Розділювач 2)", expanded=True):
        Xp2 = st.slider(
            "Вихід пермеату Xp2 (recovery)",
            min_value=0.05, max_value=0.60,
            value=default_Xp2, step=0.01,
            help="Частка пермеату 2 ступеня від пермеату 1 ступеня: Gp2 = Gp1 * Xp2"
        )
        Xz2 = st.slider(
            "Ступінь знесолення Xz2 (селективність)",
            min_value=0.800, max_value=0.999,
            value=default_Xz2, step=0.001, format="%.3f",
            help="Селективність 2-ї мембрани: Cp2 = Cp1 * (1 - Xz2)"
        )
        Xr2 = st.slider(
            "Коефіцієнт рециклу Xr2",
            min_value=0.00, max_value=0.95,
            value=default_Xr2, step=0.01,
            help="Частка концентрату ступеня 2, що повертається у рецикл: Gr2 = Gk2 * Xr2"
        )
else:
    with st.sidebar.expander("⚙️ Параметри мембрани та розділювача", expanded=True):
        Xp = st.slider(
            "Вихід пермеату Xp (recovery)",
            min_value=0.05, max_value=0.60,
            value=default_Xp1, step=0.01
        )
        Xz = st.slider(
            "Ступінь знесолення Xz (селективність)",
            min_value=0.800, max_value=0.999,
            value=default_Xz1, step=0.001, format="%.3f"
        )
        Xr = st.slider(
            "Коефіцієнт рециклу Xr",
            min_value=0.00, max_value=0.95,
            value=default_Xr1, step=0.01
        )

with st.sidebar.expander("🔄 Параметри ітераційного розрахунку", expanded=False):
    max_iter = st.number_input("Максимум ітерацій", min_value=10, max_value=500, value=100, step=10)
    init_factor = st.number_input("Множник початкового Cv (Cv_init = factor * Ci)", min_value=0.5, max_value=5.0, value=1.1, step=0.1)

# 4. Виконання розрахунку
if is_two_stage:
    res = model.calculate_two_stage(
        Ci=Ci, Gv=Gv,
        Xz1=Xz1, Xp1=Xp1, Xr1=Xr1,
        Xz2=Xz2, Xp2=Xp2, Xr2=Xr2,
        max_iter=int(max_iter),
        Cv_init_factor=init_factor
    )
else:
    res = model.calculate_single_stage(
        Ci=Ci, Gv=Gv,
        Xz=Xz, Xp=Xp, Xr=Xr,
        max_iter=int(max_iter),
        Cv_init_factor=init_factor
    )

# 5. Заголовок програми
st.markdown('<div class="main-title">💧 RevOsm: Розрахунок зворотноосмотичної установки</div>', unsafe_allow_html=True)
st.markdown(
    f'<div class="sub-title">Інтерактивне моделювання матеріальних балансів ХТС з рециклом концентрату | <b>{"Двоступенева схема" if is_two_stage else "Одноступенева схема"}</b></div>',
    unsafe_allow_html=True
)

# 6. Вкладки інтерфейсу
tab_scheme, tab_charts, tab_goalseek, tab_theory = st.tabs([
    "📊 Мнемосхема та Баланс",
    "📈 Параметричний аналіз",
    "🎯 Підбір рециклу (Goal Seek)",
    "📖 Методика та Формули"
])

# ==============================================================================
# ВКЛАДКА 1: Мнемосхема та Баланс потоків
# ==============================================================================
with tab_scheme:
    # KPI картки
    kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
    
    if is_two_stage:
        with kpi1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Кінцевий пермеат (Gp2)</div>
                <div class="metric-value">{res['Gp2']:.2f} <span style="font-size:1rem;">м³/год</span></div>
            </div>
            """, unsafe_allow_html=True)
        with kpi2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Солевміст пермеату (Cp2)</div>
                <div class="metric-value">{res['Cp2']:.3f} <span style="font-size:1rem;">мг/дм³</span></div>
            </div>
            """, unsafe_allow_html=True)
        with kpi3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Загальне знесолення</div>
                <div class="metric-value">{res['desalination_degree']:.3f} <span style="font-size:1rem;">%</span></div>
            </div>
            """, unsafe_allow_html=True)
        with kpi4:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Вихід від сирої води</div>
                <div class="metric-value">{res['recovery_total']:.1f} <span style="font-size:1rem;">%</span></div>
            </div>
            """, unsafe_allow_html=True)
        with kpi5:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Загальний скид розсолу</div>
                <div class="metric-value">{res['total_waste']:.2f} <span style="font-size:1rem;">м³/год</span></div>
            </div>
            """, unsafe_allow_html=True)
    else:
        with kpi1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Витрата пермеату (Gp)</div>
                <div class="metric-value">{res['Gp']:.2f} <span style="font-size:1rem;">м³/год</span></div>
            </div>
            """, unsafe_allow_html=True)
        with kpi2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Солевміст пермеату (Cp)</div>
                <div class="metric-value">{res['Cp']:.2f} <span style="font-size:1rem;">мг/дм³</span></div>
            </div>
            """, unsafe_allow_html=True)
        with kpi3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Ступінь знесолення</div>
                <div class="metric-value">{res['desalination_degree']:.2f} <span style="font-size:1rem;">%</span></div>
            </div>
            """, unsafe_allow_html=True)
        with kpi4:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Вихід від сирої води</div>
                <div class="metric-value">{res['recovery_total']:.1f} <span style="font-size:1rem;">%</span></div>
            </div>
            """, unsafe_allow_html=True)
        with kpi5:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Скид концентрату (Gs)</div>
                <div class="metric-value">{res['Gs']:.2f} <span style="font-size:1rem;">м³/год</span></div>
            </div>
            """, unsafe_allow_html=True)

    st.write("")

    # Балансовий індикатор "великого чорного ящика"
    bal_col1, bal_col2 = st.columns([2, 1])
    with bal_col1:
        if res['is_ok']:
            st.markdown(f"""
            <div class="badge-ok">
                ✅ Матеріальний баланс "Великого чорного ящика" зійшовся!<br>
                <small style="font-weight: normal; color: #1B5E20;">
                    Прихід солей (LP) = <b>{res['LP']:.2f} г/год</b> | 
                    Витрата солей (RP) = <b>{res['RP']:.2f} г/год</b> | 
                    Нев'язка Δ = <b>{res['delta_salt']:.2e} г/год</b> (похибка &lt; 0.001%)
                </small>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="badge-warn">
                ⚠️ Нев'язка балансу перевищує 0.001 г/год (Δ = {res['delta_salt']:.4f})
            </div>
            """, unsafe_allow_html=True)
    with bal_col2:
        st.info(f"Ітерацій розрахунку: **{res['iterations_run']}** | Збіжність: **{'Так' if res['converged'] else 'Досягнуто ліміт'}**")

    st.markdown("---")

    # Технологічна мнемосхема установки (PFD)
    st.subheader("🗺️ Технологічна мнемосхема потоків установки")
    st.caption("Значення витрат (м³/год) та солевмісту (мг/дм³) розраховуються динамічно в реальному часі:")
    
    if is_two_stage:
        dot_code = model.get_dot_two_stage(res)
    else:
        dot_code = model.get_dot_single_stage(res)
        
    st.graphviz_chart(dot_code, use_container_width=True)

    # Зведена таблиця матеріального балансу
    st.subheader("📋 Таблиця матеріального балансу потоків")
    df_streams = res["streams_df"].copy()
    
    # Форматування чисел для відображення
    df_display = df_streams.copy()
    df_display["Витрата G (м³/год)"] = df_display["Витрата G (м³/год)"].map(lambda x: f"{x:.3f}")
    df_display["Солевміст C (мг/дм³)"] = df_display["Солевміст C (мг/дм³)"].map(lambda x: f"{x:.3f}")
    df_display["Потік солі G·C (г/год)"] = df_display["Потік солі G·C (г/год)"].map(lambda x: f"{x:.2f}")

    st.dataframe(df_display, use_container_width=True, hide_index=True)

    csv_data = df_streams.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 Завантажити матеріальний баланс у CSV",
        data=csv_data,
        file_name="material_balance_ro.csv",
        mime="text/csv"
    )

# ==============================================================================
# ВКЛАДКА 2: Графіки та параметричний аналіз
# ==============================================================================
with tab_charts:
    st.subheader("📈 Параметричні залежності та збіжність розрахунку")

    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.markdown("##### 1. Динаміка збіжності ітераційного процесу")
        df_hist = res["history"]
        target_col = "Cv1" if is_two_stage else "Cv"
        
        fig_conv = go.Figure()
        fig_conv.add_trace(go.Scatter(
            x=df_hist["iteration"],
            y=df_hist[target_col],
            mode="lines+markers",
            name=f"Солевміст {target_col}",
            line=dict(color="#1976D2", width=2.5),
            marker=dict(size=5)
        ))
        fig_conv.update_layout(
            title=f"Збіжність {target_col} за ітераціями (початок з {init_factor}·Ci)",
            xaxis_title="Номер ітерації",
            yaxis_title=f"{target_col}, мг/дм³",
            template="plotly_white",
            height=380,
            margin=dict(l=40, r=40, t=50, b=40)
        )
        st.plotly_chart(fig_conv, use_container_width=True)
        st.caption("Ітераційний процес демонструє швидку експоненційну збіжність до стаціонарного стану вже за 15-20 ітерацій.")

    with chart_col2:
        if is_two_stage:
            st.markdown("##### 2. Вплив рециклу другої ступені (Xr2)")
            df_sens = model.compute_recycle_sensitivity(
                Ci=Ci, Gv=Gv,
                Xz1=Xz1, Xp1=Xp1, Xr1=Xr1,
                Xz2=Xz2, Xp2=Xp2, Xr2=Xr2,
                vary_param="Xr2"
            )

            fig_sens = make_subplots(specs=[[{"secondary_y": True}]])
            fig_sens.add_trace(
                go.Scatter(x=df_sens["Recycle_Ratio"], y=df_sens["Cv1"], name="Cv1 перед мембраною 1", line=dict(color="#D32F2F", width=2)),
                secondary_y=False
            )
            fig_sens.add_trace(
                go.Scatter(x=df_sens["Recycle_Ratio"], y=df_sens["Cp2"], name="Cp2 (пермеат 2)", line=dict(color="#00897B", width=2)),
                secondary_y=True
            )
            fig_sens.update_layout(
                title="Залежність солевмісту Cv1 та Cp2 від Xr2",
                xaxis_title="Коефіцієнт рециклу 2 ступені (Xr2)",
                template="plotly_white",
                height=380,
                margin=dict(l=40, r=40, t=50, b=40)
            )
            fig_sens.update_yaxes(title_text="Cv1, мг/дм³", secondary_y=False)
            fig_sens.update_yaxes(title_text="Cp2, мг/дм³", secondary_y=True)
            st.plotly_chart(fig_sens, use_container_width=True)
            st.caption("При збільшенні рециклу Xr2 концентрат 2 ступеня частково розбавляє вихідну воду, знижуючи Cv1.")
        else:
            st.markdown("##### 2. Вплив рециклу Xr на продуктивність та скид")
            r_vals = np.linspace(0.0, 0.9, 30)
            data_1s = []
            for r in r_vals:
                r1 = model.calculate_single_stage(Ci=Ci, Gv=Gv, Xz=Xz, Xp=Xp, Xr=r)
                data_1s.append({"Xr": r, "Gi": r1["Gi"], "Gs": r1["Gs"], "Cv": r1["Cv"]})
            df_1s = pd.DataFrame(data_1s)

            fig_1s = make_subplots(specs=[[{"secondary_y": True}]])
            fig_1s.add_trace(go.Scatter(x=df_1s["Xr"], y=df_1s["Gi"], name="Витрата свіжої води Gi", line=dict(color="#1976D2", width=2)), secondary_y=False)
            fig_1s.add_trace(go.Scatter(x=df_1s["Xr"], y=df_1s["Gs"], name="Скид концентрату Gs", line=dict(color="#C62828", width=2)), secondary_y=False)
            fig_1s.add_trace(go.Scatter(x=df_1s["Xr"], y=df_1s["Cv"], name="Солевміст Cv", line=dict(color="#F57C00", width=2, dash="dot")), secondary_y=True)
            fig_1s.update_layout(title="Вплив рециклу Xr на баланс води та солей", xaxis_title="Коефіцієнт рециклу Xr", template="plotly_white", height=380)
            fig_1s.update_yaxes(title_text="Витрата, м³/год", secondary_y=False)
            fig_1s.update_yaxes(title_text="Cv, мг/дм³", secondary_y=True)
            st.plotly_chart(fig_1s, use_container_width=True)

    # Додатковий аналіз: витрати води та скиди
    if is_two_stage:
        st.markdown("##### 3. Баланс води при варіюванні рециклу Xr2")
        fig_water = go.Figure()
        fig_water.add_trace(go.Scatter(x=df_sens["Recycle_Ratio"], y=df_sens["Gii"], mode="lines", name="Забір вихідної води Gi", line=dict(color="#0288D1", width=2)))
        fig_water.add_trace(go.Scatter(x=df_sens["Recycle_Ratio"], y=df_sens["Total_Waste"], mode="lines", name="Сумарний скид стічних вод (Gs1+Gs2)", line=dict(color="#E53935", width=2)))
        fig_water.add_trace(go.Scatter(x=df_sens["Recycle_Ratio"], y=df_sens["Gp2"], mode="lines", name="Кінцевий пермеат Gp2", line=dict(color="#00897B", width=2, dash="dash")))
        fig_water.update_layout(
            xaxis_title="Коефіцієнт рециклу Xr2",
            yaxis_title="Витрата, м³/год",
            template="plotly_white",
            height=340
        )
        st.plotly_chart(fig_water, use_container_width=True)

# ==============================================================================
# ВКЛАДКА 3: Інженерний підбір рециклу (Goal Seek)
# ==============================================================================
with tab_goalseek:
    if is_two_stage:
        st.subheader("🎯 Автоматичний розрахунок рециклу Xr2 (двоступенева схема)")
        st.markdown("""
        Відповідно до методичних вказівок (Розділ 4.3):
        > *«Однією з цілей розрахунку є визначення методом підбору рециклу другої ступені **Xr2**, 
        за якого солевміст води на вході у мембрану першого ступеня дорівнює солевмісту вихідної води ($C_{v1} = C_i$)».*
        """)

        # Точний аналітичний розрахунок (миттєвий, без натискання жодних кнопок)
        opt_xr2 = model.calculate_analytical_xr2(
            Xr1=Xr1, Xp1=Xp1, Xz1=Xz1, Xp2=Xp2, Xz2=Xz2
        )
        opt_res = model.calculate_two_stage(
            Ci=Ci, Gv=Gv,
            Xz1=Xz1, Xp1=Xp1, Xr1=Xr1,
            Xz2=Xz2, Xp2=Xp2, Xr2=opt_xr2
        )

        st.info(
            f"💡 **Фізико-хімічна закономірність**: солевміст вихідної води **$C_i = {Ci:.1f}$ мг/дм³** "
            f"**не впливає** на необхідну величину коефіцієнта $X_{{r2}}$! "
            f"Для виконання умови $C_{{v1}} = C_i$ значення $X_{{r2}}$ залежить виключно від селективності ($X_z$), "
            f"виходу пермеату ($X_p$) та рециклу 1 ступеня ($X_{{r1}} = {Xr1:.2f}$)."
        )

        gs_col1, gs_col2 = st.columns([1, 2])

        with gs_col1:
            st.markdown("##### 📌 Розрахований оптимальний рецикл:")
            st.markdown(f"""
            <div style="background-color: #E8F5E9; border: 2px solid #66BB6A; border-radius: 10px; padding: 15px; text-align: center; margin-bottom: 12px;">
                <div style="font-size: 0.88rem; color: #2E7D32; font-weight: 600;">Оптимальний Xr2 для умови Cv1 = Ci</div>
                <div style="font-size: 2.3rem; font-weight: 700; color: #1B5E20;">{opt_xr2*100:.2f}%</div>
                <div style="font-size: 0.95rem; color: #388E3C;">(частка: <b>{opt_xr2:.4f}</b>)</div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
            - **Цільовий $C_{{v1}}$**: `{Ci:.1f} мг/дм³` (точно $C_i$)
            - **Отриманий $C_{{v1}}$**: `{opt_res['Cv1']:.2f} мг/дм³`
            - **Солевміст рециклу $C_{{kk}}$**: `{opt_res['Ckk']:.2f} мг/дм³`
            """)

        with gs_col2:
            st.markdown("##### 📊 Порівняння: поточна схема vs оптимальний режим:")
            comp_df = pd.DataFrame([
                {"Параметр": "Коефіцієнт рециклу Xr2", "Поточний розрахунок": f"{Xr2:.4f} ({Xr2*100:.1f}%)", "При оптимальному Xr2": f"{opt_xr2:.4f} ({opt_xr2*100:.2f}%)"},
                {"Параметр": "Солевміст Cv1 перед мембраною (мг/дм³)", "Поточний розрахунок": f"{res['Cv1']:.2f}", "При оптимальному Xr2": f"{opt_res['Cv1']:.2f} (= Ci)"},
                {"Параметр": "Кінцевий пермеат Cp2 (мг/дм³)", "Поточний розрахунок": f"{res['Cp2']:.4f}", "При оптимальному Xr2": f"{opt_res['Cp2']:.4f}"},
                {"Параметр": "Забір вихідної води Gi (м³/год)", "Поточний розрахунок": f"{res['Gii']:.2f}", "При оптимальному Xr2": f"{opt_res['Gii']:.2f}"},
                {"Параметр": "Сумарний скид стічних вод (м³/год)", "Поточний розрахунок": f"{res['total_waste']:.2f}", "При оптимальному Xr2": f"{opt_res['total_waste']:.2f}"},
                {"Параметр": "Загальний вихід пермеату (%)", "Поточний розрахунок": f"{res['recovery_total']:.2f}%", "При оптимальному Xr2": f"{opt_res['recovery_total']:.2f}%"},
            ])
            st.table(comp_df)

    else:
        st.subheader("🎯 Автоматичний підбір коефіцієнта рециклу Xr (одноступенева схема)")
        st.markdown("""
        Визначення коефіцієнта рециклу **Xr**, за якого солевміст суміші перед мембраною досягає заданого значення $C_v$ 
        (наприклад, гранично допустимого за умовами солевідкладення сульфату кальцію).
        """)

        target_cv_1s = st.slider(
            "Оберіть цільовий солевміст Cv перед мембраною (мг/дм³):",
            min_value=float(Ci),
            max_value=float(Ci * 3.0),
            value=float(res['Cv']),
            step=25.0
        )

        opt_xr, opt_res = model.find_optimal_xr_single_stage(
            target_Cv=target_cv_1s,
            Ci=Ci, Gv=Gv,
            Xz=Xz, Xp=Xp
        )

        gs_col1, gs_col2 = st.columns([1, 2])
        with gs_col1:
            st.markdown(f"""
            <div style="background-color: #E8F5E9; border: 2px solid #66BB6A; border-radius: 10px; padding: 15px; text-align: center; margin-bottom: 12px;">
                <div style="font-size: 0.88rem; color: #2E7D32; font-weight: 600;">Необхідний рецикл Xr</div>
                <div style="font-size: 2.3rem; font-weight: 700; color: #1B5E20;">{opt_xr*100:.2f}%</div>
                <div style="font-size: 0.95rem; color: #388E3C;">(частка: <b>{opt_xr:.4f}</b>)</div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown(f"""
            - **Цільовий $C_v$**: `{target_cv_1s:.1f} мг/дм³`
            - **Отриманий $C_v$**: `{opt_res['Cv']:.2f} мг/дм³`
            """)

        with gs_col2:
            comp_df = pd.DataFrame([
                {"Параметр": "Коефіцієнт рециклу Xr", "Поточний розрахунок": f"{Xr:.4f}", "Оптимальний підбір": f"{opt_xr:.4f}"},
                {"Параметр": "Солевміст Cv (мг/дм³)", "Поточний розрахунок": f"{res['Cv']:.2f}", "Оптимальний підбір": f"{opt_res['Cv']:.2f}"},
                {"Параметр": "Солевміст пермеату Cp (мг/дм³)", "Поточний розрахунок": f"{res['Cp']:.2f}", "Оптимальний підбір": f"{opt_res['Cp']:.2f}"},
                {"Параметр": "Забір вихідної води Gi (м³/год)", "Поточний розрахунок": f"{res['Gi']:.2f}", "Оптимальний підбір": f"{opt_res['Gi']:.2f}"},
                {"Параметр": "Скид розсолу Gs (м³/год)", "Поточний розрахунок": f"{res['Gs']:.2f}", "Оптимальний підбір": f"{opt_res['Gs']:.2f}"},
            ])
            st.table(comp_df)



# ==============================================================================
# ВКЛАДКА 4: Методика та Формули
# ==============================================================================
with tab_theory:
    st.subheader("📖 Методичні основи розрахунку матеріальних балансів ХТС")
    st.markdown("""
    Відповідно до універсальної методики розрахунку хіміко-технологічних систем (ХТС), будь-яка схема розділення складається з базових вузлів трьох типів:
    
    #### 1. Зворотноосмотична мембрана (`membrana`)
    Мембранний модуль під тиском розділяє потік живлення $G_v$ з солевмістом $C_v$ на очищений пермеат ($G_p$) та концентрат ($G_k$):
    """)
    st.latex(r"G_p = G_v \cdot X_p, \quad G_k = G_v - G_p")
    st.latex(r"C_p = C_v \cdot (1 - X_z), \quad C_k = \frac{G_v \cdot C_v - G_p \cdot C_p}{G_k}")
    st.markdown("""
    де $X_p$ — вихід пермеату (recovery factor, зазвичай 0.1 ÷ 0.25);  
    $X_z$ ($X_{ob}$) — коефіцієнт затримання солей (селективність мембрани, зазвичай 0.95 ÷ 0.995).

    #### 2. Розділювач потоку концентрату (`rozdiluvach`)
    Потік концентрату ділиться на рециркуляційний потік $G_r$, що повертається на початок установки, та потік стічних вод $G_s$:
    """)
    st.latex(r"G_r = G_k \cdot X_r, \quad G_s = G_k - G_r")
    st.markdown("""
    де $X_r$ — ступінь (частка) рециркуляції концентрату.

    #### 3. Змішувачі потоків (`zmishyvach`, `zmish2`)
    - **Змішувач двох рециклів 1-ї та 2-ї ступенів**:
    """)
    st.latex(r"G_{rr} = G_{r1} + G_{r2}, \quad C_{kk} = \frac{G_{r1} \cdot C_{k1} + G_{r2} \cdot C_{k2}}{G_{rr}}")
    st.markdown("""
    - **Змішувач перед першою мембраною**:
    """)
    st.latex(r"G_i = G_v - G_{rr}, \quad C_v = \frac{G_{rr} \cdot C_{kk} + G_i \cdot C_i}{G_v}")

    st.markdown("""
    #### 4. Принцип "Великого чорного ящика" (Black Box Balance Check)
    Критерієм правильності та фізичної коректності розрахунку є закон збереження маси: сумарний прихід солей з сирою водою ($LP$) повинен точно дорівнювати сумі солей, що виходять з установки з пермеатом та стічними водами ($RP$):
    """)
    st.latex(r"LP = G_i \cdot C_i")
    st.latex(r"RP = G_{p2} \cdot C_{p2} + G_{s1} \cdot C_{k1} + G_{s2} \cdot C_{k2}")
    st.latex(r"\Delta = |LP - RP| \le 0.0001 \text{ г/год}")

    st.markdown("---")
    st.caption("Програму розроблено на основі Colab-ноутбука з розрахунком двоступеневого зворотного осмосу та методичних вказівок ХТС.")
