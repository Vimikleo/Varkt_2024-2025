import json
import matplotlib.pyplot as plt

def plot_launch_data():
    """
    Считывает Data_vzlet, строит 3 графика:
    1) Масса от времени
    2) Высота от времени
    3) Скорость (вертикальная) от времени
    """

    with open("Data_vzlet.json", "r", encoding="utf-8") as f:
        data_vzlet = json.load(f)

    # Разбиваем на отдельные списки
    # data_vzlet[i] = [mass, h, v_vert, v_total, UT]
    t_arr = [point[4] for point in data_vzlet]
    m_arr = [point[0] for point in data_vzlet]
    h_arr = [point[1] for point in data_vzlet]
    v_vert_arr = [point[2] for point in data_vzlet]
    v_all_arr = [point[3] for point in data_vzlet]

    # Чтобы "обнулить" время и смотреть от 0:
    t0 = t_arr[0]
    t_arr = [t - t0 for t in t_arr]

    # 1) График масса(t)
    plt.figure(figsize=(10, 6))
    plt.plot(t_arr, m_arr, label="Масса, kg")
    plt.title("Зависимость массы от времени (Взлёт)")
    plt.xlabel("t, сек от старта")
    plt.ylabel("Масса, кг")
    plt.grid(True)
    plt.legend()
    plt.show()

    # 2) График высота(t)
    plt.figure(figsize=(10, 6))
    plt.plot(t_arr, h_arr, color='green', label="Высота, м")
    plt.title("Зависимость высоты от времени (Взлёт)")
    plt.xlabel("t, сек от старта")
    plt.ylabel("Высота над поверхностью, м")
    plt.grid(True)
    plt.legend()
    plt.show()

    # 3) График скорость(t) — возьмём вертикальную скорость
    plt.figure(figsize=(10, 6))
    plt.plot(t_arr, v_vert_arr, color='red', label="Вертикальная скорость, м/с")
    plt.title("Зависимость вертикальной скорости от времени (Взлёт)")
    plt.xlabel("t, сек от старта")
    plt.ylabel("V_vert, м/с")
    plt.grid(True)
    plt.legend()
    plt.show()


def plot_landing_data():
    """
    Считывает Data_landing, строит 3 графика:
    1) Масса от времени
    2) Высота от времени
    3) Скорость (вертикальная) от времени
    """

    with open("Data_landing.json", "r", encoding="utf-8") as f:
        data_landing = json.load(f)

    # data_landing[i] = [mass, h, v_vert, UT]
    t_arr = [point[3] for point in data_landing]
    m_arr = [point[0] for point in data_landing]
    h_arr = [point[1] for point in data_landing]
    v_vert_arr = [point[2] for point in data_landing]

    # Снова "обнуляем" время, чтобы начинать с t=0
    t0 = t_arr[0]
    t_arr = [t - t0 for t in t_arr]

    # 1) График масса(t)
    plt.figure(figsize=(10, 6))
    plt.plot(t_arr, m_arr, label="Масса, kg")
    plt.title("Зависимость массы от времени (Посадка)")
    plt.xlabel("t, сек от начала снижения")
    plt.ylabel("Масса, кг")
    plt.grid(True)
    plt.legend()
    plt.show()

    # 2) График высота(t)
    plt.figure(figsize=(10, 6))
    plt.plot(t_arr, h_arr, color='green', label="Высота, м")
    plt.title("Зависимость высоты от времени (Посадка)")
    plt.xlabel("t, сек от начала снижения")
    plt.ylabel("Высота над поверхностью, м")
    plt.grid(True)
    plt.legend()
    plt.show()

    # 3) График вертикальная скорость(t)
    plt.figure(figsize=(10, 6))
    plt.plot(t_arr, v_vert_arr, color='red', label="Вертикальная скорость, м/с")
    plt.title("Зависимость вертикальной скорости от времени (Посадка)")
    plt.xlabel("t, сек от начала снижения")
    plt.ylabel("V_vert, м/с")
    plt.grid(True)
    plt.legend()
    plt.show()


if __name__ == "__main__":
    # Построим графики по взлёту
    plot_launch_data()
    # Построим графики по посадке
    plot_landing_data()