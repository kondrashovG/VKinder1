from vk_api.keyboard import VkKeyboard, VkKeyboardColor
import vk.bot
import database
import configparser
from datetime import date, datetime
# from pprint import pprint
import vk.searcher

if __name__ == "__main__":
    API_URL = 'https://api.vk.com/method/'
    config = configparser.ConfigParser()  # создаём объекта парсера
    config.read("settings.ini")  # читаем конфиг
    bot = vk.bot.Bot(config["Tokens"]["bot"])
    comm_token = config["Tokens"]["comm"]
    user_token = config["Tokens"]["VK"]
    VK1 = vk.searcher.VK(user_token, API_URL)
    DB = database.VKinderDB(password='postgres')
    cached_users = {}
    candidate = []
    some_list = []
    current = []
    what_list = True


    @bot.message_handler("Начать")  # Декоратор добавляющий обработчик на определённое сообщение
    def hello(msg):
        global cached_users, candidate
        client = cached_users.get(msg.user_id)
        black_list = []
        if client is None:
            client = VK1.get_info(msg.user_id)[0]
            client_sex = {1: 2, 2: 1}[client["sex"]]
            today = date.today()
            birth_date = datetime.strptime(client["bdate"], '%d.%m.%Y')
            client_age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
            client_city = client["city"]["title"]
            [black_list.append(i[0]) for i in DB.favorites_list(msg.user_id, False)]
            list_candidates = VK1.search_users(sex=client_sex, age_at=client_age, age_to=client_age, city=client_city)
            client = [client["id"], client["first_name"], client["last_name"], client["bdate"], client_city,
                      client["sex"], list_candidates, black_list]
            photos = VK1.get_vk_photo(client[0])
            gender = (client[5] == 2)
            DB.insert_client(owner_id=client[0], name=client[1], surname=client[2],
                             birthday=client[3], city=client[4], gender=gender, photo=photos)
            cached_users.update([(msg.user_id, client)])
            print("Всего1:", len(list_candidates))
        elif len(client[6]) == 0:
            client_sex = {1: 2, 2: 1}[client[5]]
            today = date.today()
            birth_date = datetime.strptime(client[3], '%d.%m.%Y')
            client_age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
            client[6] = VK1.search_users(sex=client_sex, age_at=client_age, age_to=client_age, city=client[4])
            [black_list.append(i[0]) for i in DB.favorites_list(msg.user_id, False)]
            client[7] = black_list
            cached_users.update([(msg.user_id, client)])
            print("Всего2:", len(client[6]))
        keyboard = VkKeyboard(one_time=True)
        keyboard.add_button('Следующий', color=VkKeyboardColor.POSITIVE)
        keyboard.add_button('Избранное', color=VkKeyboardColor.POSITIVE)
        keyboard.add_button('Чёрный список', color=VkKeyboardColor.POSITIVE)
        keyboard = keyboard.get_keyboard()
        bot.send_message(msg.user_id, f'{client[0]}, {client[4]}\nЗдравствуйте, {client[1]} {client[2]}!', keyboard)


    @bot.message_handler("Следующий")
    def find_vk(msg):
        global cached_users, candidate
        keyboard = VkKeyboard(one_time=True)
        while True:
            if len(cached_users.get(msg.user_id)[6]) == 0:
                keyboard.add_button('Начать', color=VkKeyboardColor.POSITIVE)
                keyboard = keyboard.get_keyboard()
                bot.send_message(msg.user_id, f'Список закончился. Если хотите начать заново, нажмите "Начать"',
                                 keyboard)
                return
            candidate = cached_users.get(msg.user_id)[6].pop()
            if candidate[0] not in cached_users.get(msg.user_id)[7]:
                break
        keyboard.add_button('Запомнить', color=VkKeyboardColor.POSITIVE)
        keyboard.add_button('В чёрный список', color=VkKeyboardColor.POSITIVE)
        keyboard.add_button('Следующий', color=VkKeyboardColor.POSITIVE)
        keyboard = keyboard.get_keyboard()
        photos = ''
        for i in candidate[5]:
            photos += bot.create_photo_attachment(i) + ','
        bot.send_message(msg.user_id, f'{candidate[1]} {candidate[2]}\n{candidate[3]}\n{candidate[4]}\n',
                         keyboard, photos)


    @bot.message_handler("Запомнить")
    def call_list1(msg):
        favorites(msg, True)


    @bot.message_handler("В чёрный список")
    def call_list2(msg):
        favorites(msg, False)


    @bot.message_handler("Избранное")
    def call_list3(msg):
        print('См. Избранное')
        list_check(msg, True)


    @bot.message_handler("Чёрный список")
    def call_list4(msg):
        print('См. Чёрный список')
        list_check(msg, False)


    @bot.message_handler("Удалить из списка")
    def del_from_list(msg):
        global some_list, current
        DB.delete_from_list(owner_id=msg.user_id, vk_id=current[0])
        keyboard = VkKeyboard(one_time=True)
        keyboard.add_button('Следующий из списка', color=VkKeyboardColor.POSITIVE)
        keyboard = keyboard.get_keyboard()
        w_l = {True: 'Избранных', False: 'чёрного списка'}[what_list]
        bot.send_message(msg.user_id, f'запись {current[1]} {current[2]}\n{current[3]}\n удалена из {w_l}',
                         keyboard)


    @bot.message_handler("Следующий из списка")
    def next_from_list(msg):
        global some_list, current, what_list
        keyboard = VkKeyboard(one_time=True)
        if len(some_list) == 0:
            keyboard.add_button('Начать', color=VkKeyboardColor.POSITIVE)
            keyboard = keyboard.get_keyboard()
            bot.send_message(msg.user_id, f'Список закончился. Если хотите продолжить, нажмите "Начать"', keyboard)
            return
        current = some_list.pop()
        photos = ''
        for i in current[5]:
            photos += bot.create_photo_attachment(i) + ','
        keyboard.add_button('Удалить из списка', color=VkKeyboardColor.POSITIVE)
        keyboard.add_button('Следующий из списка', color=VkKeyboardColor.POSITIVE)
        keyboard = keyboard.get_keyboard()
        bot.send_message(msg.user_id, f'{current[1]} {current[2]}\n{current[3]}\n', keyboard, photos)


    def favorites(msg, b_w):
        global cached_users, candidate
        DB.insert_selected(owner_id=msg.user_id, vk_id=candidate[0], sel_ign=b_w, name=candidate[1],
                           surname=candidate[2], birthday=candidate[3], city=cached_users[msg.user_id][4],
                           gender=not cached_users[msg.user_id][5], photo=candidate[5])
        keyboard = VkKeyboard(one_time=True)
        keyboard.add_button('Следующий', color=VkKeyboardColor.POSITIVE)
        keyboard = keyboard.get_keyboard()
        w_l = {True: 'Избранные', False: 'чёрный список'}[b_w]
        bot.send_message(msg.user_id, f'запись {candidate[1]} {candidate[2]}\n{candidate[3]}\n добавлена в {w_l}',
                         keyboard)


    def list_check(msg, b_w):
        global some_list, what_list
        what_list = b_w
        some_list = []
        [some_list.append(i) for i in DB.favorites_list(msg.user_id, b_w)]
        next_from_list(msg)


    bot.infinity_polling()  # Бесконечный опрос ВК на изменения
