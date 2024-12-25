import time
import json
import krpc

# настраиваем соединение с сервером игры
conn = krpc.connect()

# получаем объекты управления
space_center = conn.space_center
vessel = conn.space_center.active_vessel
data = []  # список, в который будем писать логи посадки

# Изначально рассчитываем дистанцию до Мун; устанавливаем ускоренное время (Rails warp)
distance_to_moon = 100000000000
space_center.rails_warp_factor = 5
min_dist = 10000000000000

# Ждём приближения к Мун: пока расстояние не станет < 100000 м (здесь, видимо, 100 км или т.п.)
# Если расстояние начало расти снова — значит, мы уже прошли точку минимума, можно останавливать ускорение.
while distance_to_moon >= 100000:
    min_dist = min(min_dist, distance_to_moon)
    ship_position = space_center.active_vessel.position(space_center.active_vessel.orbit.body.reference_frame)
    moon_position = space_center.bodies["Mun"].position(space_center.active_vessel.orbit.body.reference_frame)
    distance_to_moon = ((moon_position[0] - ship_position[0]) ** 2 +
                        (moon_position[1] - ship_position[1]) ** 2 +
                        (moon_position[2] - ship_position[2]) ** 2) ** 0.5
    print(distance_to_moon, min_dist, "метров")
    if (distance_to_moon > min_dist):
        break
    time.sleep(2)

# переходим в нормальное время, завершая фазу приближения
space_center.physics_warp_factor = 0

# включаем двигатель для выравнивания орбиты на Мун:
# ставим SAS в режим Retrograde (торможение по ретроградному вектору),
# задаём газ на максимум и ждём пока апоапсис и периапсис не сравняются (примерно).
vessel.control.sas_mode = vessel.control.sas_mode.retrograde
vessel.control.throttle = 1
time.sleep(2)
apoapsis_altitude = 10 ** 14
periapsis_altitude = 0

# Выравнивание орбиты: пока разница большой и малой высот орбиты больше 10^6, продолжаем ждать.
while abs(periapsis_altitude - apoapsis_altitude) > 10 ** 6:
    vessel = space_center.active_vessel
    orbit = vessel.orbit
    apoapsis_altitude = orbit.apoapsis_altitude
    periapsis_altitude = orbit.periapsis_altitude
    time.sleep(1)
space_center.physics_warp_factor = 0

# Отстыковка лишней ступени перед посадкой — вызываем дважды activate_next_stage()
vessel.control.activate_next_stage()
vessel.control.activate_next_stage()

print("Орбита луны успешно выровнена")
time.sleep(3)

################################################################################################################
# переход к посадке

# выставляем SAS в режим Retrograde для посадки
vessel.control.sas_mode = vessel.control.sas_mode.retrograde

# Ставим «триггер» на значение перицентра (periapsis_altitude),
# если оно станет меньше -198000, считаем, что корабль пошёл на пересечение поверхности.
pere_altitude = conn.get_call(getattr, vessel.orbit, 'periapsis_altitude')
expr = conn.krpc.Expression.less_than(
    conn.krpc.Expression.call(pere_altitude),
    conn.krpc.Expression.constant_double(-198000))
event = conn.krpc.add_event(expr)

# включаем двигатель и ждём события — как только условие сработает,
# throttle будет обнулён, значит мы входим на траекторию посадки
vessel.control.throttle = 1
with event.condition:
    event.wait()
vessel.control.throttle = 0
time.sleep(1)

# Ускоряем время до тех пор, пока не достигнем 25 км над поверхностью
space_center.rails_warp_factor = 5
while vessel.flight(vessel.orbit.body.reference_frame).surface_altitude > 25000:
    time.sleep(0.1)
    continue
space_center.physics_warp_factor = 0

# Ждём, пока высота не станет 21 км (тормозим в реальном времени)
while vessel.flight(vessel.orbit.body.reference_frame).surface_altitude > 21000:
    time.sleep(0.1)
    continue

h = 1
V = 1


# Алгоритм оценки, достаточно ли «упасть», чтобы начинать финальное торможение.
# F — тяга, cos_f — косинус угла тяги (здесь = 1, т.е. полный упор вниз),
# k — некоторая поправка для изменения массы (с учётом расхода топлива)
while h > 0 or V > 2:
    F = 60000
    cos_f = 1
    #k = 3.54
    k = 13
    m0 = vessel.mass
    h = vessel.flight(vessel.orbit.body.reference_frame).surface_altitude
    GM = 6.5138398 * 10 ** 10  # гравитационный параметр (для Луны)
    r = 200_000               # примерный радиус орбиты расчёта
    V = vessel.flight(vessel.orbit.body.reference_frame).vertical_speed
    dt = 0.01
    t = 0
    current_ut = space_center.ut

    # логируем текущие показатели
    data.append([m0, h, V, current_ut])
    time.sleep(0.1)

    # «псевдо»-просчёт изменения V и высоты, пока вертикальная скорость отрицательна (падает)
    while V < 0 and h > 0:
        t += 0.01
        dVy = ((F * cos_f) / (m0 - k * t) - GM / ((r + h) ** 2)) * dt
        V = V + dVy
        dh = V * dt
        h = h + dh

    print(h, V)

# Включаем двигатель для посадки (throttle = 1) и выпускаем шасси
vessel.control.throttle = 1
vessel.control.legs = True

# «Грубая» (верхняя) часть посадки: следим, чтобы вертикальная скорость не превышала -12 м/с,
# если -12 и ниже — полный газ, если -8 и выше (то есть медленно падаем), — выключаем двигатель на время
while vessel.flight(vessel.orbit.body.reference_frame).surface_altitude > 20:
    current_ut = space_center.ut
    v = vessel.flight(vessel.orbit.body.reference_frame).vertical_speed
    h = vessel.flight(vessel.orbit.body.reference_frame).surface_altitude
    data.append([vessel.mass, h, v, current_ut])
    time.sleep(0.1)

    if v < -12:
        vessel.control.throttle = 1
    elif v > -8:
        vessel.control.throttle = 0
        time.sleep(1)
    time.sleep(0.1)

# Финальные метры (меньше 20 м над поверхностью): плавная корректировка
while vessel.flight(vessel.orbit.body.reference_frame).surface_altitude > 5:
    current_ut = space_center.ut
    v = vessel.flight(vessel.orbit.body.reference_frame).vertical_speed
    h = vessel.flight(vessel.orbit.body.reference_frame).surface_altitude
    data.append([vessel.mass, h, v, current_ut])
    time.sleep(0.1)

    if v < -2:
        vessel.control.throttle = 0.25
    elif v > -2:
        vessel.control.throttle = 0
        time.sleep(1)
    time.sleep(0.1)

# Отключаем двигатель — мы должны мягко коснуться поверхности
vessel.control.throttle = 0
print("Успешная посадка!")

# Сохраняем логи посадки в JSON
with open("Data_landing.json", 'w', encoding="UTF-8") as file:
    json.dump(data, file, ensure_ascii=False, indent=2)

# Закрываем соединение
conn.close()