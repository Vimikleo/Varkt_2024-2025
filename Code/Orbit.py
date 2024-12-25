import time
import os
import krpc

# подключаемся к kRPC-серверу (KSP)
conn = krpc.connect(name='Launch into orbit')
# получаем объекты управления
space_center = conn.space_center
vessel = conn.space_center.active_vessel

# настраиваем автопилот: включаем SAS, выставляем режим Prograde
vessel.control.sas = True
vessel.control.sas_mode = vessel.control.sas_mode.prograde
time.sleep(0.5)

# включаем глобальное ускорение времени (Rails warp), чтобы быстрее дождаться нужного угла
space_center.rails_warp_factor = 10

# Ждём, пока угол между нашим кораблём и Мун (вектор из центра Кербина) не попадёт в нужный диапазон.
# Здесь используется cos(fi), чтобы оценить «угол».
k = 0
while True:
    # координаты корабля в референс-фрейме планеты
    ship_position = space_center.active_vessel.position(space_center.active_vessel.orbit.body.reference_frame)
    # координаты Луны (Mun)
    moon_position = space_center.bodies["Mun"].position(space_center.active_vessel.orbit.body.reference_frame)

    # раскладываем вектора
    v1 = [ship_position[0], ship_position[1], ship_position[2]]
    v2 = [moon_position[0], moon_position[1], moon_position[2]]

    # вычисляем косинус угла между векторами (через скалярное произведение)
    cosfi = (v1[0] * v2[0] + v1[1] * v2[1] + v1[2] * v2[2]) / (
            ((v1[0] ** 2 + v1[1] ** 2 + v1[2] ** 2) ** 0.5) * ((v2[0] ** 2 + v2[1] ** 2 + v2[2] ** 2) ** 0.5))

    # Если косинус угла стал в нужном промежутке (примерно -0.8...-0.76), считаем, что «окно» подошло.
    if cosfi > -0.8 and cosfi < -0.76:
        k += 1
        time.sleep(0.5)
    # Два срабатывания подряд — «надёжная» проверка (убираем случайные колебания)
    if k >= 2:
        break

# возвращаем физический варп (Physics Warp) к 0, чтобы аккуратно делать манёвр
space_center.physics_warp_factor = 0

# начинаем разгон на переходную орбиту
print("Начало разгона")

# выставляем режим SAS на Prograde, полный газ
vessel.control.sas_mode = vessel.control.sas_mode.prograde
vessel.control.throttle = 1

# целевая скорость — текущая орбитальная + примерно 800 м/с (подобрано эмпирически)
dv = space_center.active_vessel.orbit.speed + 800

# крутим двигатель, пока не достигнем этой скорости
while space_center.active_vessel.orbit.speed < dv:
    print(space_center.active_vessel.orbit.speed, dv)
    time.sleep(0.1)

# останавливаем двигатель
vessel.control.throttle = 0

# закрываем соединение
conn.close()

# подтверждение, что мы «ушли» на необходимую траекторию
print("fil swaped")

time.sleep(2)

# запускаем следующий файл — перелёт и посадка на Мун
file = "TR.py"
os.system(f'python {file}')