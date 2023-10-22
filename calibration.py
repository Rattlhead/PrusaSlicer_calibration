# -------------------------- Импорт библиотек --------------------------

import argparse  # Импорт модуля обработки аргументов командной строки
import sys
from os import getenv  # Импорт модуля для получения значений переменных окружения

# Необходимо для получения параметров профиля PrusaSlicer 

# ------------- Получение аргументов переданных сценарию ---------------


parser = argparse.ArgumentParser()

parser.add_argument('--retract', default='0', help='Начальное значение длины ретракта, мм')
parser.add_argument('--step', default='0', help='Шаг изменения для калибровки (ретракта, скорости, температуры)')
parser.add_argument('--step_height', default='3', help='Высота одного шага калибровки, мм')
parser.add_argument('--step_layers', default='0', help='Количество слоёв одного шага калибровки')
parser.add_argument('--speed', default='0', help='Скорость ретракта, мм/сек')
parser.add_argument('--temp', default='0', help='Начальное значение калибровки температуры')
parser.add_argument('--separator', default='0', help='Включить разделитель на модели')
parser.add_argument('--nola', default='-1', help='Калибровка NOLA')
parser.add_argument('file', help="Путь к g-коду", nargs="+")

args = parser.parse_args()

file_input = args.file[0]  # Извлечение аргумента, путь к временному g-коду
if len(args.file) > 1:  # Если аргументов 2,
    file_output = args.file[1]  # использовать 2-й аргумент для отладки
else:
    file_output = file_input  # иначе записывать результат в исходный файл
file_output = file_output


# ------------------- Создание всех важных переменных ----------------------

debag_list: str = ''  # Список со всеми настройками
index_line: int = 0  # Счётчик строк
index_step: int = 1  # Счётчик шагов
last_index_step: int = 0
flag: bool = False  # Чтобы не затронуть пользовательский код
height_search: float = 0.0

marker_z: str = ";Z:"  # Метка текущей высоты Z

step: float = float(args.step)
retract = float(args.retract)
retract_speed = int(args.speed)
temperature = float(args.temp)
nola = float(args.nola)

separator = bool(int(args.separator))  # Сделать отметку на печати
separator_check: bool = False  # Метка поставлен разделитель
# ------------------- Защита от дурака ----------------------

# Проверка на включенную функцию "Использовать относительные координаты экструдера"
# if not int(getenv('SLIC3R_USE_RELATIVE_E_DISTANCES')):
#     sys.exit(
#         '\n Включите функцию "Использовать относительные координаты экструдера" \n Настройки принтера -> Общие -> Дополнительно (Красный)')

# Проверка на выключенную функцию "Очистка сопла при ретракте"
if str(getenv('SLIC3R_FILAMENT_WIPE')) == 'nil':
    if int(getenv('SLIC3R_WIPE')):
        sys.exit(
            '\n Снимите галочку в функции "Очистка сопла при ретракте" \n Настройки принтера -> Экструдер (Желтый)')
elif int(getenv('SLIC3R_FILAMENT_WIPE')):
    sys.exit(
        '\n Снимите галочку в функции "Очистка сопла при ретракте" \n Настройки прутка -> Переопределить параметры (Желтый)')

# Не задан шаг калибровки
if not step:
    sys.exit('\n Не задан шаг калибровки --step ')



# ------------------- Вывод всех настроек ----------------------
debag_list += "\n; file_input = " + file_input + \
              "\n; file_output = " + file_output + \
              "\n; step_height = " + str(args.step_height) + \
              "\n; step_layers = " + str(args.step_layers) + \
              "\n; step = " + str(args.step) + \
              "\n; temp = " + str(args.temp) + \
              "\n; retract = " + str(args.retract) + \
              "\n; speed = " + str(args.speed) + \
              "\n; separator = " + str(separator) + \
              "\n; nola = " + str(nola) + \
              '\n '

# ------------------- Извлечение данных из g-кода ----------------------


layer_height = float(getenv('SLIC3R_LAYER_HEIGHT'))

debag_list += '\n; Высота слоя (взято из слайсера) = ' + str(layer_height)

# ------------------- Преднастройка ----------------------



# Если ретракт не задан, то берется значение из слайсера
if not retract:
    set_retract = float(getenv('SLIC3R_FILAMENT_RETRACT_LENGTH'))
else:
    debag_list += '\n; Калибруется длина ретракта'
    set_retract = float(args.retract)

# Если скорость не задана, то берется значение из слайсера
if not retract_speed:
    set_speed = float(getenv('SLIC3R_FILAMENT_RETRACT_SPEED'))
else:
    debag_list += '\n; Калибруется скорость ретракта'
    set_speed = float(args.speed)

# Если температура не задана, то берется значение из слайсера
if not temperature:
    set_temp = float(getenv('SLIC3R_TEMPERATURE'))
else:
    debag_list += '\n; Калибруется температура'
    set_temp = int(args.temp)

# Высота секции в мм
if int(args.step_layers):
    height_step_search = int(args.step_layers) * layer_height  # Если задали кол-во слоев, то высота вычисляется
else:
    height_step_search = float(args.step_height)  # Если нет, то берется высота в мм

print(height_step_search)

# -------------------------- Изменение кода ----------------------------

with open(file_input, 'r') as file:  # Открываем файл для чтения
    lines = file.readlines()  # Заносим все строки файла в список

for line in lines:  # Обработка списка из строк файла

    speed = int(set_speed) * 60

    if index_step > last_index_step:
        debag_list += '\n; Сегмент {0} – Начало секции {1}мм, Ретракт {2}мм, Скорость {3}мм/с Температура {4}C, Nola {5}'. \
            format(str(index_step), str(height_search), str(set_retract), str(set_speed), str(set_temp), str(nola))
        last_index_step = index_step

    if marker_z in line:  # Ищем отметку высоты слоя

        if separator and separator_check:
            lines[index_line] += 'M221 S100 ;Вернуть поток к норме 100\n'
            separator_check = False

        height_current = float(line[len(marker_z):])  # Текущая высота
        # print(f'Текущая высота слоя - {height_current}')
        height_search = float(index_step * height_step_search)  # Искомая высота
        # print(f'Высота которую мы ищем - {height_search}')

        if height_current == layer_height: # первый слой
            if nola >= 0:
                lines[index_line] += f'M117 {nola} \n'

                lines[index_line] += 'M900 O' + str(nola) + ' R0.5\n'
            if temperature:
                lines[index_line] += 'M117 Temperature ' + str(set_temp) + '\nM104 ' + str(set_temp) + '\n'


        if round(abs(height_current - height_search), 2) < layer_height:  # Если искомая высота равна текущей

            if separator:
                lines[index_line] += 'M221 S200 ;Увеличить поток для разделителя\n'
                separator_check = True

            if nola >= 0:
                nola += step
                nola = float('{:.2f}'.format(nola))
                lines[index_line+2] += f'M117 {nola} \n'
                lines[index_line+2] += 'M900 O' + str(nola) + '\n'


            # Калибровка ретракта
            # Длина ретракта
            if retract:
                set_retract += step
                set_retract = float('{:.2f}'.format(set_retract))
                lines[index_line] += 'M117 Retract len - ' + str(set_retract) + '\n'

            # Скорость ретракта
            if retract_speed:
                set_speed += step
                set_speed = float('{:.2f}'.format(set_speed))
                lines[index_line] += 'M117 Retract speed - ' + str(int(set_speed)) + '\n'

            # Калибровка температура, только если она задана
            if temperature:
                set_temp += step
                set_temp = float('{:.2f}'.format(set_temp))
                lines[index_line] += 'M117 Temperature ' + str(set_temp) + '\nM104 S' + str(set_temp) + '\n'

            index_step += 1

    # Калибровка ретракта только если они включены
    if retract or retract_speed:

        # Начало работы кода
        if ';LAYER_CHANGE' in line:
            flag = True

        # Конец работы кода
        if ';END gcode for filament' in line:
            flag = False

        if flag:
            # print('меняется ретракт')
            if "G1 E-" in line:
                lines[index_line] = 'G1 E-' + str(set_retract) + ' F' + str(set_speed * 60) + ' ;My retract\n'

            elif "G1 E" in line:
                lines[index_line] = 'G1 E' + str(set_retract) + ' F' + str(set_speed * 60) + ' ;My unretract\n'

    index_line += 1  # Увеличение счётчика строк

lines[0] = '\n\n' + debag_list + '\n;------------------------\n' + lines[0]

gcode = ''.join(lines)  # Объединение строк после обработки

with open(file_output, 'w') as file:  # Открываем файл c G-code для записи
    file.write(gcode)  # Записываем результат обработки в файл
