from vk_api.keyboard import VkKeyboard, VkKeyboardColor
import vk.bot
import database
import configparser
from datetime import date, datetime
# from pprint import pprint
import vk.searcher

if __name__ == "__main__":
    # API_URL = 'https://api.vk.com/method/'
    config = configparser.ConfigParser()  # создаём объекта парсера
    config.read("settings.ini")  # читаем конфиг
    bot = vk.bot.Bot(config["Tokens"]["bot"])
    comm_token = config["Tokens"]["comm"]
    user_token = config["Tokens"]["VK"]
    VK1 = vk.searcher.VK(user_token, config["Urls"]["API_URL"])
    DB = database.VKinderDB(password='postgres')
    cached_users = {}  # cловарь клиентов в текущем сеансе бота. Ключ - VKid клиента, значение - список данных клиента
    candidate = []  # список кандидатов клиента, полученных по запросу из VK
    some_list = []  # список (Избранное или Чёрный список)
    current = []  # текущая запись из some_list
    what_list = True  # признак списка (True - Избранное, False - Чёрный список)


    @bot.message_handler("Начать")  # Декоратор добавляющий обработчик на определённое сообщение
    def hello(msg):
        """
        :param msg: содержит VKid клиента (msg.user_id)
        :return: nothing

        Начальная процедура диалога с клиентом. Выводится приветствие в чате, в БД вносятся данные о клиенте. Из БД
        извлекается Чёрный список его кандидатов. Из VK поисковый запрос формирует список кандидатов для клиента.
        Для продолжения формируются 3 кнопки:
            → - перейти к просмотру следующего кандидата, синяя кнопка
            ❤ - перейти к просмотру списка Избранных клиента, зелёная кнопка
            ❌ - перейти к просмотру Чёрного списка, белая кнопка
        """
        global cached_users, candidate
        client = cached_users.get(msg.user_id)
        black_list = []
        if client is None:
            client = VK1.get_info(msg.user_id)[0]
            client_sex = {1: 2, 2: 1}[client["sex"]]
            today = date.today()
            birth_date = datetime.strptime(client["bdate"], '%d.%m.%Y')
            client_age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
            client_city = client["city"]["id"]
            [black_list.append(i[0]) for i in DB.favorites_list(msg.user_id, False)]
            list_candidates = VK1.search_users(sex=client_sex, age_at=client_age, age_to=client_age, city=client_city)
            client = [client["id"], client["first_name"], client["last_name"], client["bdate"], client_city,
                      client["sex"], list_candidates, black_list]
            photos = VK1.get_vk_photo(client[0])
            gender = (client[5] == 2)
            DB.insert_client(owner_id=client[0], name=client[1], surname=client[2],
                             birthday=client[3], city=client[4], gender=gender, photo=photos)
            cached_users.update([(msg.user_id, client)])
        elif len(client[6]) == 0:
            client_sex = {1: 2, 2: 1}[client[5]]
            today = date.today()
            birth_date = datetime.strptime(client[3], '%d.%m.%Y')
            client_age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
            client[6] = VK1.search_users(sex=client_sex, age_at=client_age, age_to=client_age, city=client[4])
            [black_list.append(i[0]) for i in DB.favorites_list(msg.user_id, False)]
            client[7] = black_list
            cached_users.update([(msg.user_id, client)])
        keyboard = VkKeyboard(one_time=True)
        keyboard.add_button('→', color=VkKeyboardColor.PRIMARY)
        keyboard.add_button('❤', color=VkKeyboardColor.POSITIVE)
        keyboard.add_button('❌', color=VkKeyboardColor.SECONDARY)
        keyboard = keyboard.get_keyboard()
        s_msg = f'{client[0]}, {client[4]}\nЗдравствуйте, {client[1]} {client[2]}\nНазначение кнопок:\n' \
                f'❤ - просмотр Избранных(зелёная кнопка)\n❌ - просмотр Чёрного списка(белая кнопка)\n' \
                f'→ - следующий кандидат(синяя кнопка)\nВозраст для поиска: {client_age}\n'
        bot.send_message(msg.user_id, s_msg, keyboard)


    @bot.message_handler("→")
    def find_vk(msg):
        """
        :param msg: содержит VKid клиента (msg.user_id)
        :return: nothing

        Процедура обработки текущего кандидата из VK. В чате выводится информация о кандидате, 3 его самых популярных
        фото, ссылка на профиль. Если кандидат в Чёрном списке, он пропускается, обрабатываются следующий.
        Для продолжения формируются 3 кнопки:
            → - перейти к просмотру следующего кандидата, синяя кнопка
            →❤ - внести кандидата в список Избранных, зелёная кнопка
            →❌ - внести кандидата в Чёрный список, белая кнопка
        Если список кандидатов исчерпан, предлагается 1 кнопка:
            Начать - начать диалог сначала (процедура hello), синяя кнопка
        Специальной кнопки окончания чата не предусмотрено. Клиент может закрыть чат в любой момент.
        """
        global cached_users, candidate
        keyboard = VkKeyboard(one_time=True)
        while True:
            if len(cached_users.get(msg.user_id)[6]) == 0:
                keyboard.add_button('Начать', color=VkKeyboardColor.PRIMARY)
                keyboard = keyboard.get_keyboard()
                bot.send_message(msg.user_id,
                                 f'Список выборки из VK закончился. Если хотите начать заново, нажмите "Начать"',
                                 keyboard)
                return
            candidate = cached_users.get(msg.user_id)[6].pop()
            if candidate[0] not in cached_users.get(msg.user_id)[7]:
                break
        keyboard.add_button('→❤', color=VkKeyboardColor.POSITIVE)
        keyboard.add_button('→❌', color=VkKeyboardColor.SECONDARY)
        keyboard.add_button('❤', color=VkKeyboardColor.POSITIVE)
        keyboard.add_button('❌', color=VkKeyboardColor.SECONDARY)
        keyboard.add_line()
        keyboard.add_button('→', color=VkKeyboardColor.PRIMARY)
        keyboard.add_button('Начать', color=VkKeyboardColor.PRIMARY)
        keyboard = keyboard.get_keyboard()
        photos = ''
        for i in candidate[5]:
            photos += bot.create_photo_attachment(i) + ','
        s_msg = f'{candidate[1]} {candidate[2]}\n{candidate[3]}\n{candidate[4]}\nНазначение кнопок:\n' \
                f'→❤ - записать в Избранные(зелёная кнопка)\n→❌ - внести в Чёрный список(белая кнопка)\n' \
                f'❤ - просмотр Избранных(зелёная кнопка)\n❌ - просмотр Чёрного списка(белая кнопка)\n' \
                f'→ - следующий кандидат(синяя кнопка)\nДля повтора поиска нажмите "Начать"(синяя кнопка)'
        bot.send_message(msg.user_id, s_msg, keyboard, photos)


    @bot.message_handler("→❤")
    def call_list1(msg):
        """
            :param msg: содержит VKid клиента (msg.user_id)
            :return: nothing

            Процедура инициирует вызов функции favorites для добавления кандидата в список Избранных
        """
        favorites(msg, True)


    @bot.message_handler("→❌")
    def call_list2(msg):
        """
            :param msg: содержит VKid клиента (msg.user_id)
            :return: nothing

            Процедура инициирует вызов функции favorites для добавления кандидата в Чёрный список
        """
        favorites(msg, False)


    @bot.message_handler("❤")
    def call_list3(msg):
        """
            :param msg: содержит VKid клиента (msg.user_id)
            :return: nothing

            Процедура инициирует вызов функции list_check для просмотра списка Избранных
        """
        print('См. Избранное')
        list_check(msg, True)


    @bot.message_handler("❌")
    def call_list4(msg):
        """
            :param msg: содержит VKid клиента (msg.user_id)
            :return: nothing

            Процедура инициирует вызов функции list_check для просмотра Чёрного списка
        """
        print('См. Чёрный список')
        list_check(msg, False)


    @bot.message_handler("✖")
    def del_from_list(msg):
        """
            :param msg: содержит VKid клиента (msg.user_id)
            :return: nothing

            Процедура для удаления записи из Чёрного списка или списка Избранных
        """
        global some_list, current
        DB.delete_from_list(owner_id=msg.user_id, vk_id=current[0])
        keyboard = VkKeyboard(one_time=True)
        keyboard.add_button('❤', color=VkKeyboardColor.POSITIVE)
        keyboard.add_button('❌', color=VkKeyboardColor.SECONDARY)
        keyboard.add_button('►', color=VkKeyboardColor.PRIMARY)
        keyboard.add_button('Начать', color=VkKeyboardColor.PRIMARY)
        keyboard = keyboard.get_keyboard()
        w_l = {True: '❤', False: '❌'}[what_list]
        s_msg = f'запись {current[1]} {current[2]}\n{current[3]}\n удалена из {w_l}\nНазначение кнопок:\n' \
                f'❤ - просмотр Избранных(зелёная кнопка)\n❌ - просмотр Чёрного списка(белая кнопка)\n' \
                f'► - следующий кандидат из списка {w_l}(синяя кнопка)\n' \
                f'Для повтора поиска нажмите "Начать"(синяя кнопка)'
        bot.send_message(msg.user_id, s_msg, keyboard)


    @bot.message_handler("►")
    def next_from_list(msg):
        """
            :param msg: содержит VKid клиента (msg.user_id)
            :return: nothing

            Процедура для обработки текущей записи из Чёрного списка или списка Избранных. В чате выводится информация о
        кандидате, 3 его фото, ссылка на профиль.
        Для продолжения формируются 2 кнопки:
            ► - перейти к просмотру следующей записи в списке, синяя кнопка
            ✖ - удалить кандидата из просматриваемого списка, белая кнопка
        Если список кандидатов исчерпан, предлагается 1 кнопка:
            Начать - начать диалог сначала (процедура hello), синяя кнопка
        """
        global some_list, current, what_list
        keyboard = VkKeyboard(one_time=True)
        keyboard.add_button('❤', color=VkKeyboardColor.POSITIVE)
        keyboard.add_button('❌', color=VkKeyboardColor.SECONDARY)
        bot.send_message(msg.user_id,
                         f'❤ - просмотр Избранных(зелёная кнопка)\n❌ - просмотр Чёрного списка(белая кнопка)\n')
        keyboard.add_button('Начать', color=VkKeyboardColor.PRIMARY)
        if len(some_list) == 0:
            keyboard = keyboard.get_keyboard()
            w_l = {True: '❤', False: '❌'}[what_list]
            bot.send_message(msg.user_id, f'Список {w_l} закончился. Для повтора поиска нажмите "Начать"', keyboard)
            return
        current = some_list.pop()
        photos = ''
        for i in current[5]:
            photos += bot.create_photo_attachment(i) + ','
        keyboard.add_line()
        keyboard.add_button('✖', color=VkKeyboardColor.SECONDARY)
        keyboard.add_button('►', color=VkKeyboardColor.PRIMARY)
        keyboard = keyboard.get_keyboard()
        s_msg = f'{current[1]} {current[2]}\n{current[3]}\nНазначение кнопок:\n' \
                f'✖ - удалить из списка(белая кнопка)\n► - следующий кандидат из списка(синяя кнопка)\n' \
                f'Для повтора поиска нажмите "Начать"(синяя кнопка)'
        bot.send_message(msg.user_id, s_msg, keyboard, photos)


    def favorites(msg, b_w):
        """
            :param msg: содержит VKid клиента (msg.user_id)
            :param b_w: True - список Избранных, False - Чёрный список
            :return: nothing

        Процедура добавляет кандидата в Чёрный список или список Избранных. Информация о кандидате заносится в
            БД VKinder.
        Для продолжения предлагается 1 кнопка:
            → - перейти к просмотру следующего кандидата, синяя кнопка
        """
        global cached_users, candidate
        if len(candidate[3]) < 6:
            candidate[3] += '.' + cached_users[msg.user_id][3][-4:]
        print(cached_users[msg.user_id][5])
        DB.insert_selected(owner_id=msg.user_id, vk_id=candidate[0], sel_ign=b_w, name=candidate[1],
                           surname=candidate[2], birthday=candidate[3], city=cached_users[msg.user_id][4],
                           gender=(cached_users[msg.user_id][5] == 1), photo=candidate[5])
        keyboard = VkKeyboard(one_time=True)
        keyboard.add_button('→', color=VkKeyboardColor.PRIMARY)
        keyboard = keyboard.get_keyboard()
        w_l = {True: 'Избранные', False: 'чёрный список'}[b_w]
        bot.send_message(msg.user_id, f'запись {candidate[1]} {candidate[2]}\n{candidate[3]}\n добавлена в {w_l}',
                         keyboard)


    def list_check(msg, b_w):
        """
            :param msg: содержит VKid клиента (msg.user_id)
            :param b_w: True - список Избранных, False - Чёрный список
            :return: nothing

        Процедура извлекает из БД VKinder Чёрный список или список Избранных. Затем вызывает процедуру
        next_from_list, предназначенной для работы с элементами извлеченного списка.
        """
        global some_list, what_list
        what_list = b_w
        some_list = []
        [some_list.append(i) for i in DB.favorites_list(msg.user_id, b_w)]
        next_from_list(msg)


    bot.infinity_polling()  # Бесконечный опрос ВК на изменения
