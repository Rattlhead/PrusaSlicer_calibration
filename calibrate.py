# ------------------------------ Описание ------------------------------

'''

За основу был взят скрипт demonlibra
https://uni3d.store/viewtopic.php?t=1041

Сценарий калибровка ретракта (скорость,длина),температуры. Версия 1.0

Подробности в чате Ulti STEEL RepRap Firmware:
https://t.me/ultireprap

Включите функцию "Использовать относительные координаты экструдера"
    Настройки принтера -> Общие -> Дополнительно (Красный)

Снимите галочку в функции "Очистка сопла при ретракте"
    Настройки прутка -> Переопределить параметры (Желтый)

Снимите галочку в функции "Очистка сопла при ретракте"
    Настройки принтера -> Экструдер (Желтый)

Рекомендации по калибровке ретрактов:
    Разместите два цилиндра на краях стола.
    Количество периметров: 1 или 2
    Количество слоёв крышки и дна: 0

Добавьте в список скриптов постобработки пути к интепритатору и сценарию с аргументами.

Например:
/usr/bin/python3 /путь до файла/calibrate.py

MacOS
/usr/local/bin/python3 /путь до файла/calibrate.py

Аргументы сценария:

    --retract=...       Включает калибровку ретрактка и задает начальное значение (по умолчанию 0 - выключено)
    --retract 2         Скорость берется из слайсера FILAMENT_RETRACT_SPEED (Настройки прутка -> Переопределить параметры)
    --retract 0.15

	--temp=...          Включает калибровку температуры и задает начальное значение (по умолчанию 0 - выключено)
    --temp 200

	--step=...			Шаг изменения для ретракта, скорости, температуры (по умолчанию 0)
    --step 0.25
    --step 10

	--step_height=...	Высота печати с одной длиной ретракта, мм (по умолчанию 3)
    --step_height 5

	--step_layers=...	Количество слоёв с одной длиной ретракта, мм (по умолчанию 0 - выключено)
	--step_layers 2		Если указать step_layers, не будет использоваться step_height
    --step_layers 15

	--speed=...			Включает калибровку скорость ретракта, мм/сек (по умолчанию 0 - выключено)
	--speed 40          Длина берется из слайсера FILAMENT_RETRACT_LENGTH (Настройки прутка -> Переопределить параметры)

	--separator=...     Увеличивает поток на один слой, тем самым создавая некий визуальный разделитель (по умолчанию 0 - выключено)
    --separator 1       Тестовая функция
    --separator 0

	--z_hope=...		Подъём головы при ретракте, мм (по умолчанию 0). Не реализован, управляется слайсером.


'''

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
parser.add_argument('--z_hope', default='0', help='Подъём головы при ретракте, мм')
parser.add_argument('--temp', default='0', help='Начальное значение калибровки температуры')
parser.add_argument('--separator', default='0', help='Включить разделитель на модели')
parser.add_argument('file', help="Путь к g-коду", nargs="+")

args = parser.parse_args()

file_input = args.file[0]  # Извлечение аргумента, путь к временному g-коду
if len(args.file) > 1:  # Если аргументов 2,
    file_output = args.file[1]  # использовать 2-й аргумент для отладки
else:
    file_output = file_input  # иначе записывать результат в исходный файл
file_output = file_output

# ------------------- Защита от дурака ----------------------

# Проверка на включенную функцию "Использовать относительные координаты экструдера"
if not int(getenv('SLIC3R_USE_RELATIVE_E_DISTANCES')):
    sys.exit(
        '\n Включите функцию "Использовать относительные координаты экструдера" \n Настройки принтера -> Общие -> Дополнительно (Красный)')

# Проверка на выключенную функцию "Очистка сопла при ретракте"
if str(getenv('SLIC3R_FILAMENT_WIPE')) == 'nil':
    if int(getenv('SLIC3R_WIPE')):
        sys.exit(
            '\n Снимите галочку в функции "Очистка сопла при ретракте" \n Настройки принтера -> Экструдер (Желтый)')
elif int(getenv('SLIC3R_FILAMENT_WIPE')):
    sys.exit(
        '\n Снимите галочку в функции "Очистка сопла при ретракте" \n Настройки прутка -> Переопределить параметры (Желтый)')

# ------------------- Создание всех важных переменных ----------------------

debag_list = ''  # Список со всеми настройками
index_line = 0  # Счётчик строк
index_step = 1  # Счётчик шагов
last_index_step = 0
flag = False  # Для ретракта чтобы не затронуть пользовательский и конечный код
height_search = 0.0
retract = float(args.retract)
retract_speed = int(args.speed)
temperature = float(args.temp)
separator = bool(int(args.separator))  # Сделать отметку на печати
separator_check = False  # Метка поставлен разделитель

# ------------------- Дебаг ----------------------
debag_list += "\nfile_input = " + file_input + \
              "\nfile_output = " + file_output + \
              "\nstep_height = " + str(args.step_height) + \
              "\nstep_layers = " + str(args.step_layers) + \
              "\nstep = " + str(args.step) + \
              "\ntemp = " + str(args.temp) + \
              "\nretract = " + str(args.retract) + \
              "\nspeed = " + str(args.speed) + \
              "\nseparator = " + str(separator) + \
              '\n '

# ------------------- Извлечение данных из g-кода ----------------------

marker_z = ";Z:"  # Метка текущей высоты Z

with open(file_input) as file:
    for line in file:  # Перебор строк файла

        if marker_z in line:  # Поиск максимальной высоты печати
            model_height = line[len(marker_z):]
            model_height = float(model_height)

debag_list += "\nВысота_печати = " + str(model_height)
layer_height = float(getenv('SLIC3R_LAYER_HEIGHT'))

debag_list += '\nВысота слоя (взято из слайсера) = ' + str(layer_height)

# ------------------- Преднастройка ----------------------

step = float(args.step)

# Если ретракт не задан, то берется значение из слайсера
if not retract:
    set_retract = float(getenv('SLIC3R_FILAMENT_RETRACT_LENGTH'))
else:
    debag_list += '\nКалибруется длина ретракта'
    set_retract = float(args.retract)

# Если скорость не задана, то берется значение из слайсера
if not retract_speed:
    set_speed = float(getenv('SLIC3R_FILAMENT_RETRACT_SPEED'))
else:
    debag_list += '\nКалибруется скорость ретракта'
    set_speed = float(args.speed)

# Если температура не задана, то берется значение из слайсера
if not temperature:
    set_temp = int(getenv('SLIC3R_TEMPERATURE'))
else:
    debag_list += '\nКалибруется температура'
    set_temp = int(args.temp)

# Высота секции в мм
if int(args.step_layers):
    height_step_search = int(args.step_layers) * layer_height  # Если задали кол-во слоев, то высота вычисляется
else:
    height_step_search = float(args.step_height)  # Если нет, то берется высота в мм

print(height_step_search)

# -------------------------- Изменение кода ----------------------------

with open(file_input) as file:  # Открываем файл для чтения
    lines = file.readlines()  # Заносим все строки файла в список

for line in lines:  # Обработка списка из строк файла

    speed = int(set_speed) * 60

    if index_step > last_index_step:
        debag = '\nСегмент {0} – Начало секции {1}мм, Ретракт {2}мм, Скорость {3}мм/с Температура {4}C'. \
            format(str(index_step), str(height_search), str(set_retract), str(set_speed), str(set_temp))

        print(debag)
        debag_list += debag
        last_index_step = index_step

    if marker_z in line:  # Ищем отметку высоты слоя

        if separator and separator_check:
            lines[index_line] += 'M221 S100 ;Вернуть поток к норме 100\n'
            separator_check = False

        height_current = float(line[len(marker_z):])  # Текущая высота
        # print(f'Текущая высота слоя - {height_current}')
        height_search = float(index_step * height_step_search)  # Искомая высота
        # print(f'Высота которую ммы ищем - {height_search}')

        if round(abs(height_current - height_search), 2) < layer_height:  # Если искомая высота равна текущей

            if separator:
                lines[index_line] += 'M221 S200 ;Увеличить поток для разделителя\n'
                separator_check = True

            # Калибровка ретракта
            # Длина ретракта
            if retract:
                set_retract += step
                lines[index_line] += 'M117 Retract len - ' + str(set_retract) + '\n'

            # Скорость ретракта
            if retract_speed:
                set_speed += step
                lines[index_line] += 'M117 Retract speed - ' + str(int(set_speed)) + '\n'

            # Калибровка температура, только если она задана
            if temperature:
                set_temp += step
                lines[index_line] += 'M117 Temperature ' + str(set_temp) + '\nM104 ' + str(set_temp) + '\n'

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

lines[0] = '\n\n' + debag_list + '\n------------------------\n' + lines[0]

gcode = ''.join(lines)  # Объединение строк после обработки

with open(file_output, 'w') as file:  # Открываем файл c G-code для записи
    file.write(gcode)  # Записываем результат обработки в файл
