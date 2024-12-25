# импорт используемых библиотек
import math   # для математических функций и констант
import time   # для управления временем и паузами
import krpc   # библиотека для взаимодействия с KSP через kRPC
import os     # для запуска внешних команд (скриптов)
import json   # для сохранения логов в формате JSON


def log():
    """
    Функция для логирования основных параметров полёта.
    Сохраняет в список data следующие данные:
    - Текущая масса корабля
    - Высота над поверхностью
    - Вертикальная скорость
    - Полная скорость (векторная сумма по X, Y, Z)
    - Текущее игровое время (UT)
    Затем делает небольшую паузу (0.3 с) перед следующим вызовом.
    """
    global data
    current_ut = space_center.ut
    # Вертикальная скорость
    v = vessel.flight(vessel.orbit.body.reference_frame).vertical_speed
    # Компоненты вектора скорости
    vector_v_all = vessel.flight(vessel.orbit.body.reference_frame).velocity
    # Полная (скалярная) скорость — вычисление по формуле sqrt(vx^2 + vy^2 + vz^2)
    v_all = (vector_v_all[0] ** 2 + vector_v_all[1] ** 2 + vector_v_all[2] ** 2) ** 0.5
    # Высота над поверхностью
    h = vessel.flight(vessel.orbit.body.reference_frame).surface_altitude

    # Добавляем всю информацию в массив data
    data.append([vessel.mass, h, v, v_all, current_ut])

    # Небольшая задержка
    time.sleep(0.3)


# выставляем необходимые параметры орбиты
turn_start_altitude = 250      # высота, на которой начинается наклон корабля (гравитурн)
turn_end_altitude = 45000      # высота, на которой наклон корабля заканчивается
target_altitude = 150000       # требуемая высота апоapsиса (целевые 150 км)

# настраиваем соединение с сервером игры KSP
conn = krpc.connect(name='Launch into orbit')

# получаем объекты из соединения
vessel = conn.space_center.active_vessel    # ссылка на активный корабль
space_center = conn.space_center            # ссылка на космический центр
tech_stage = 7                              # номер текущей ступени (менять под конкретную ракету)

# создаём потоки для удобного чтения параметров:
ut = conn.add_stream(getattr, conn.space_center, 'ut')  # текущее игровое время
altitude = conn.add_stream(getattr, vessel.flight(), 'mean_altitude')  # высота над уровнем моря (mean)
apoapsis = conn.add_stream(getattr, vessel.orbit, 'apoapsis_altitude') # высота апоапсиса орбиты
stage_resources = vessel.resources_in_decouple_stage(stage=tech_stage, cumulative=False)
stage_fuel = conn.add_stream(stage_resources.amount, 'LiquidFuel')     # поток для чтения топлива в текущей ступени

# подготавливаем корабль перед взлётом
vessel.control.sas = False     # отключаем автостабилизацию SAS (будем управлять вручную или автопилотом)
vessel.control.rcs = False     # отключаем RCS
vessel.control.throttle = 1.0  # выкручиваем газ на максимум
turn_angle = 0                 # начальный угол наклона
data = []                      # массив, в который будем собирать лог полёта

# выводим небольшой обратный отсчёт
print('3...')
time.sleep(1)
print('2...')
time.sleep(1)
print('1...')
time.sleep(1)
print('Взлет!')

# включаем двигатель (активируем следующую ступень)
vessel.control.activate_next_stage()

# включаем автопилот и выставляем начальные углы (вертикально вверх)
vessel.auto_pilot.engage()
vessel.auto_pilot.target_pitch_and_heading(90, 90)

# Основной цикл взлёта
while True:

    # Снимаем показатели и пишем в лог
    log()

    # Если достигли высоты начала гравитурна и не превысили высоту окончания,
    # плавно меняем угол наклона от 90° к 0° (по тангажу).
    if altitude() > turn_start_altitude and altitude() < turn_end_altitude:
        frac = ((altitude() - turn_start_altitude) /
                (turn_end_altitude - turn_start_altitude))
        new_turn_angle = frac * 90
        # чтобы не задавать угол автопилоту слишком часто, меняем только если разница > 0.5°
        if abs(new_turn_angle - turn_angle) > 0.5:
            turn_angle = new_turn_angle
            vessel.auto_pilot.target_pitch_and_heading(90 - turn_angle, 90)


    # Когда топливо в текущей ступени заканчивается, отстыковываемся и переходим к следующей
    if stage_fuel() < 0.1:
        vessel.control.activate_next_stage()
        tech_stage -= 1
        time.sleep(1)
        stage_resources = vessel.resources_in_decouple_stage(stage=tech_stage, cumulative=False)
        stage_fuel = conn.add_stream(stage_resources.amount, 'LiquidFuel')
        time.sleep(1)
        print('stage separated', tech_stage, stage_fuel())

    # Как только апоапсис достигает ~90% от целевого (т.е. 135 км при цели 150 км), завершаем основной разгон
    if apoapsis() > target_altitude * 0.9:
        print('Approaching target apoapsis')
        break

# Уменьшаем тягу при приближении к апоapsису
vessel.control.throttle = 0.25
while apoapsis() < target_altitude:
    # пока апоапсис меньше целевой высоты, понемногу дожигаем
    log()

# Останавливаем разгон — целевая высота апоапсиса (150 км) примерно достигнута
vessel.control.throttle = 0.0

# Ждём выхода из атмосферы (70 км — верхняя граница атмосферы Кербина)
while altitude() < 70500:
    log()

# Сохраняем лог взлёта в файл
with open("Data_vzlet.json", 'w', encoding="UTF-8") as file:
    json.dump(data, file, ensure_ascii=False, indent=2)

# Проверяем, что данные действительно записаны
if len(data) != 0:
    print("Лог взлета записан!")

# Планируем манёвр закругления орбиты (циркуляризацию) на апоапсисе
print('Planning circularization burn')

# Вычисляем дельта-V для перевода эллиптической орбиты в круговую
mu = vessel.orbit.body.gravitational_parameter  # гравитационный параметр планеты
r = vessel.orbit.apoapsis                      # радиус апоапсиса
a1 = vessel.orbit.semi_major_axis              # текущая большая полуось
a2 = r                                         # целевая (круговая) большая полуось
v1 = math.sqrt(mu * ((2. / r) - (1. / a1)))    # текущая орбитальная скорость на апоапсисе
v2 = math.sqrt(mu * ((2. / r) - (1. / a2)))    # желаемая скорость на том же радиусе (круговая)
delta_v = v2 - v1                              # разница (сколько нужно добавить)

# Добавляем узел манёвра через time_to_apoapsis секунд от текущего UT
node = vessel.control.add_node(ut() + vessel.orbit.time_to_apoapsis, prograde=delta_v)

# Расчёт времени сжигания (burn_time) с учётом специфического импульса и доступной тяги
F = vessel.available_thrust               # доступная тяга
Isp = vessel.specific_impulse * 9.82       # эффективная тяга (Учёт g0 ~ 9.82 м/с^2)
m0 = vessel.mass                           # начальная масса корабля
m1 = m0 / math.exp(delta_v / Isp)          # масса после сжигания топлива
flow_rate = F / Isp                        # расход топлива (кг/с)
burn_time = (m0 - m1) / flow_rate          # время сжигания

# Готовим автопилот к манёвру (ориентируемся на узел манёвра)
vessel.auto_pilot.reference_frame = node.reference_frame
vessel.auto_pilot.target_direction = (0, 1, 0)  # направление «прогрейд» в системе отсчёта узла
vessel.auto_pilot.wait()

# Прокручиваем время до момента начала манёвра (за половину burn_time до апоапсиса)
burn_ut = ut() + vessel.orbit.time_to_apoapsis - (burn_time / 2.)
lead_time = 5
conn.space_center.warp_to(burn_ut - lead_time)

# Ждём, пока не придёт время манёвра (time_to_apoapsis ~ burn_time/2)
time_to_apoapsis = conn.add_stream(getattr, vessel.orbit, 'time_to_apoapsis')
while time_to_apoapsis() - (burn_time / 2.) > 0:
    pass

# Выполняем манёвр
vessel.control.throttle = 1.0
time.sleep(burn_time - 0.1)
vessel.control.throttle = 0.05


# Следим за оставшимся импульсом; когда он достигнет определённого минимума, останавливаем двигатель
remaining_burn = conn.add_stream(node.remaining_burn_vector, node.reference_frame)
fl = True
while remaining_burn()[1] > 0.5:
    # если топливо снова заканчивается на этапе манёвра, переключаемся на следующую ступень
    if stage_fuel() < 0.1:
        vessel.control.activate_next_stage()
        tech_stage -= 1
        time.sleep(1)
        stage_resources = vessel.resources_in_decouple_stage(stage=tech_stage, cumulative=False)
        stage_fuel = conn.add_stream(stage_resources.amount, 'LiquidFuel')
        time.sleep(1)
        fl = False

vessel.control.throttle = 0.0
node.remove()  # удаляем узел (манёвр выполнен)

# Проверяем оставшееся топливо. Если fl == True, значит мы ещё не переключали ступень в процессе манёвра,
# поэтому делаем дополнительное «прожигание» (activate_next_stage) дважды (зависит от конструкции ракеты).
if fl == True:
    vessel.control.activate_next_stage()
    vessel.control.activate_next_stage()
time.sleep(2)

# Закрываем соединение с сервером
conn.close()

# Пишем сообщение о завершении вывода на орбиту и запускаем следующий скрипт
print("Взлет завершен!")
file = "Orbit.py"
os.system(f'python {file}')