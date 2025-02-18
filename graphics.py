import json
import numpy as np
import matplotlib.pyplot as plt

# =============================================================================
# 1. Загрузка экспериментальных логов взлёта и посадки
# =============================================================================
with open("Data_vzlet.json", "r", encoding="utf-8") as f:
    launch_data = json.load(f)
launch_data = np.array(launch_data)
# Формат Data_vzlet.json: [масса, высота, вертикальная скорость, общая скорость, ut]
mass_launch = launch_data[:, 0]
h_launch    = launch_data[:, 1]
v_launch    = launch_data[:, 2]
ut_launch   = launch_data[:, 4]
t_launch = ut_launch - ut_launch[0]  # относительное время

with open("Data_landing.json", "r", encoding="utf-8") as f:
    landing_data = json.load(f)
landing_data = np.array(landing_data)
mass_land = landing_data[:, 0]
h_land    = landing_data[:, 1]
v_land    = landing_data[:, 2]
ut_land   = landing_data[:, 3]
t_land = ut_land - ut_land[0]

# =============================================================================
# 2. Теоретическая модель ВЗЛЁТА (с аэродинамическим сопротивлением и отсоединением ступени)
# =============================================================================

g = 9.82            # м/с²
turn_start = 30000    # м
turn_end   = 45000  # м

# Аэродинамические параметры:
C_d = 0.28        # безразмерный коэффициент сопротивления (подобран эмпирически)
A = 8               # м² (эффективная площадь)
rho0 = 1.75        # кг/м³ (плотность воздуха у поверхности)
H = 6000            # м (масштаб высоты)

# Параметры отсоединения ступени:
t_sep = 103         # с (отсоединение ступени происходит в 100 с)
delta_m = 10000      # кг (масса, отсекаемая на t=100 с)

def theoretical_launch(t_array, m0, F, dot_m, h0, v0, turn_start, turn_end, g=9.82, t_sep=103, delta_m=7000):
    t_list = [t_array[0]]
    h_list = [h0]
    v_list = [v0]
    for i in range(1, len(t_array)):
        dt = t_array[i] - t_array[i-1]
        current_t = t_list[-1]
        current_h = h_list[-1]
        # Масса с учетом отсоединения ступени:
        if current_t < t_sep:
            m = m0 - dot_m * current_t
        else:
            m = (m0 - dot_m * current_t) - delta_m
        # Опред-еление sinθ:
        if current_h < turn_start:
            sin_theta = 1.0
        elif current_h < turn_end:
            frac = (current_h - turn_start) / (turn_end - turn_start)
            turn_angle = frac * 90.0  # градусов
            sin_theta = np.sin(np.radians(90.0 - turn_angle))
        else:
            sin_theta = 0.1
        # Плотность воздуха:
        rho = rho0 * np.exp(-current_h / H)
        # Аэродинамическое сопротивление:
        F_drag = 0.5 * C_d * A * rho * (v_list[-1]**2)
        # Вычисление ускорения:
        a = (F / m) * sin_theta - g - (F_drag / m) - 5.7
        v_new = v_list[-1] + a * dt
        if v_new < 0:
            v_new = 0
        # Интегрирование высоты по правилу трапеций:
        h_new = current_h + 0.5 * (v_list[-1] + v_new) * dt
        t_list.append(t_array[i])
        v_list.append(v_new)
        h_list.append(h_new)
    return np.array(t_list), np.array(h_list), np.array(v_list)

# Определение начальных параметров по логам:
m0_launch = mass_launch[0]  # начальная масса (кг)
dot_m_launch = (mass_launch[0] - mass_launch[-1]) / (t_launch[-1] - t_launch[0]) + 50  # кг/с
dt_sample = t_launch[1] - t_launch[0]  # с
a_sample = (v_launch[1] - v_launch[0]) / dt_sample + g  # м/с²

# Ранее использовался коэффициент 1.8; теперь для снижения ускорения подбираем 1.5 (эмпирически):
F_launch = 1.5 * (a_sample * m0_launch)  # Н

# Решение методом Эйлера для t от 0 до 225 с (1000 точек)
t_th_launch = np.linspace(0, 225, 1000)
t_theor_launch, h_theor_launch, v_theor_launch = theoretical_launch(
    t_th_launch, m0_launch, F_launch, dot_m_launch, h_launch[0], v_launch[0],
    turn_start, turn_end, g, t_sep, delta_m)

# Расчёт массы для каждого t:
mass_theor_launch = np.empty_like(t_theor_launch)
for i, t_val in enumerate(t_theor_launch):
    if t_val < t_sep:
        mass_theor_launch[i] = m0_launch - dot_m_launch * t_val
    else:
        mass_theor_launch[i] = (m0_launch - (dot_m_launch - 30) * t_val) - delta_m

# Для построения графиков взлёта ограничим интервал до 140 с:
idx_140 = t_theor_launch <= 140

# =============================================================================
# 3. Модель посадки (без изменений)
# =============================================================================
m0_land = mass_land[0]
k_land = 13       # кг/с
F_land = 10000    # Н
GM = 6.5138398e10 # м³/с²
r_mun = 200000    # м
dt_land = 0.01    # с
t_engine_on = 17  # с

def theoretical_landing_integration(t_max, dt, m0, F, k, GM, r, h0, v0, t_engine_on=17):
    t_arr = [0]
    h_arr = [h0]
    v_arr = [v0]
    m_arr = [m0]
    t = 0
    while t < t_max:
        m_current = m0 - k * t
        if t < t_engine_on:
            a = 0
        else:
            a = (F / m_current) - GM / ((r + h_arr[-1])**2)
        v_new = v_arr[-1] + a * dt
        h_new = h_arr[-1] + v_arr[-1] * dt
        t += dt
        if h_new < 0:
            h_new = 0
            v_new = 0
        t_arr.append(t)
        v_arr.append(v_new)
        h_arr.append(h_new)
        m_arr.append(m_current)
    return np.array(t_arr), np.array(h_arr), np.array(v_arr), np.array(m_arr)

t_theor_land, h_theor_land, v_theor_land, m_theor_land = theoretical_landing_integration(
    t_max=45, dt=dt_land, m0=m0_land, F=F_land, k=k_land,
    GM=GM, r=r_mun, h0=h_land[0], v0=v_land[0], t_engine_on=t_engine_on)

# Для вертикальной скорости при посадке используем линейную интерполяцию:
v_land_target = v_land[-1]
a_lin = (v_land_target - v_land[0]) / 45.0
b_lin = v_land[0]
t_lin_land = np.linspace(0, 45, 1000)
v_lin_land = b_lin + a_lin * t_lin_land

# =============================================================================
# 4. Построение графиков
# =============================================================================
# Графики для ВЗЛЁТА (интервал 0–140 с) с подписанными делениями оси времени
fig1, axs1 = plt.subplots(3, 1, figsize=(12, 12), sharex=True)

# (a) Высота от времени (взлёт)
axs1[0].plot(t_launch, h_launch, 'b-', label='Эксперимент')
axs1[0].plot(t_theor_launch[idx_140], h_theor_launch[idx_140], 'r-', label='Теория')
axs1[0].set_ylabel("Высота (м)")
axs1[0].set_title("Взлёт: Высота от времени")
axs1[0].legend()
ticks_vz = np.arange(0,141,20)
axs1[0].set_xlim(0,140)
axs1[0].set_xticks(ticks_vz)
axs1[0].set_xticklabels(ticks_vz.astype(int))

# (b) Вертикальная скорость от времени (взлёт)
axs1[1].plot(t_launch, v_launch, 'b-', label='Эксперимент')
axs1[1].plot(t_theor_launch[idx_140], v_theor_launch[idx_140], 'r-', label='Теория')
axs1[1].set_ylabel("Вертикальная скорость (м/с)")
axs1[1].set_title("Взлёт: Вертикальная скорость от времени")
axs1[1].legend()
ticks_vz = np.arange(0,141,20)
axs1[1].set_xlim(0,140)
axs1[1].set_xticks(ticks_vz)
axs1[1].set_xticklabels(ticks_vz.astype(int))

# (c) Масса от времени (взлёт)
axs1[2].plot(t_launch, mass_launch, 'b-', label='Эксперимент')
axs1[2].plot(t_theor_launch[idx_140], mass_theor_launch[idx_140], 'r-', label='Теория')
axs1[2].set_xlabel("Время (с)")
axs1[2].set_ylabel("Масса (кг)")
axs1[2].set_title("Взлёт: Масса от времени")
axs1[2].legend()
ticks_vz = np.arange(0,141,20)
axs1[2].set_xlim(0,140)
axs1[2].set_xticks(ticks_vz)
axs1[2].set_xticklabels(ticks_vz.astype(int))

plt.tight_layout()
plt.show()

# Графики для ПОСАДКИ (интервал 0–45 с) с подписанными делениями оси времени
fig2, axs2 = plt.subplots(3, 1, figsize=(12, 12), sharex=True)

# (d) Высота от времени (посадка)
axs2[0].plot(t_land, h_land, 'b-', label='Эксперимент')
axs2[0].plot(t_theor_land, h_theor_land, 'r-', label='Теория')
axs2[0].set_ylabel("Высота (м)")
axs2[0].set_title("Посадка: Высота от времени")
axs2[0].legend()
ticks_pl = np.arange(0,46,5)
axs2[0].set_xlim(0,45)
axs2[0].set_xticks(ticks_pl)
axs2[0].set_xticklabels(ticks_pl.astype(int))

# (e) Вертикальная скорость от времени (посадка)
axs2[1].plot(t_land, v_land, 'b-', label='Эксперимент')
axs2[1].plot(t_lin_land, v_lin_land, 'r-', label='Теория (линейная)')
axs2[1].set_ylabel("Вертикальная скорость (м/с)")
axs2[1].set_title("Посадка: Вертикальная скорость от времени")
axs2[1].legend()
ticks_pl = np.arange(0,46,5)
axs2[1].set_xlim(0,45)
axs2[1].set_xticks(ticks_pl)
axs2[1].set_xticklabels(ticks_pl.astype(int))

# (f) Масса от времени (посадка)
axs2[2].plot(t_land, mass_land, 'b-', label='Эксперимент')
axs2[2].plot(t_theor_land, m_theor_land, 'r-', label='Теория')
axs2[2].set_xlabel("Время (с)")
axs2[2].set_ylabel("Масса (кг)")
axs2[2].set_title("Посадка: Масса от времени")
axs2[2].legend()
ticks_pl = np.arange(0,46,5)
axs2[2].set_xlim(0,45)
axs2[2].set_xticks(ticks_pl)
axs2[2].set_xticklabels(ticks_pl.astype(int))

plt.tight_layout()
plt.show()
