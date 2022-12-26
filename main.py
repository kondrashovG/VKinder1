from vk_api.keyboard import VkKeyboard, VkKeyboardColor
import bot
import database
import configparser
from datetime import date, datetime
from pprint import pprint
import vk.searcher

if __name__ == "__main__":
    API_URL = 'https://api.vk.com/method/'
    config = configparser.ConfigParser()  # создаём объекта парсера
    config.read("settings.ini")  # читаем конфиг
    bot = bot.Bot(config["Tokens"]["bot"])
    comm_token = config["Tokens"]["comm"]
    user_token = config["Tokens"]["VK"]
    VK1 = vk.searcher.VK(user_token, API_URL)
    DB = database.VKinderDB(password='postgres')
    cached_users = {}


    @bot.message_handler("Начать")  # Декоратор добавляющий обработчик на определённое сообщение
    def hello(msg):
        client = cached_users.get(msg.user_id)
        pprint(cached_users)
        if client is None:
            client = VK1.get_info(msg.user_id)[0]
            client_sex = {1: 2, 2: 1}[client["sex"]]
            today = date.today()
            birth_date = datetime.strptime(client["bdate"], '%d.%m.%Y')
            client_age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
            client_city = client["city"]["title"]
            client = [client["id"], client["first_name"], client["last_name"], client["bdate"], client_city,
                      client["sex"],
                      VK1.search_users(sex=client_sex, age_at=client_age, age_to=client_age, city=client_city)]
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
            cached_users.update([(msg.user_id, client)])
        keyboard = VkKeyboard(one_time=True)
        keyboard.add_button('Следующий', color=VkKeyboardColor.POSITIVE)
        keyboard = keyboard.get_keyboard()
        bot.send_message(msg.user_id,
                         f'{client[0]}, {client[4]}\nЗдравствуйте, {client[1]} {client[2]}!',
                         keyboard)  # Отправляем ответ


    @bot.message_handler("Поиск")
    def find_vk(msg):
        @bot.message_handler("Запомнить")
        def favorites(msg):
            DB.insert_selected(owner_id=msg.user_id, vk_id=candidate[0], sel_ign=True, name=candidate[1],
                               surname=candidate[2], birthday=candidate[3], city=cached_users[msg.user_id][4],
                               gender=not cached_users[msg.user_id][5], photo=candidate[5])
            keyboard = VkKeyboard(one_time=True)
            keyboard.add_button('Следующий', color=VkKeyboardColor.POSITIVE)
            keyboard = keyboard.get_keyboard()
            bot.send_message(msg.user_id, f'{candidate[1]} {candidate[2]}\n{candidate[3]}\n добавлена в Избранное',
                             keyboard)

        keyboard = VkKeyboard(one_time=True)
        if len(cached_users.get(msg.user_id)[6]) == 0:
            keyboard.add_button('Начать', color=VkKeyboardColor.POSITIVE)
            keyboard = keyboard.get_keyboard()
            bot.send_message(msg.user_id, f'Список закончился. Если хотите начать заново, нажмите "Начать"', keyboard)
            return
        candidate = cached_users.get(msg.user_id)[6].pop()
        pprint(candidate)
        keyboard.add_button('Запомнить', color=VkKeyboardColor.POSITIVE)
        keyboard.add_button('В чёрный список', color=VkKeyboardColor.POSITIVE)
        keyboard.add_button('Следующий', color=VkKeyboardColor.POSITIVE)
        keyboard = keyboard.get_keyboard()
        photos = ''
        for i in candidate[5]:
            photos += bot.create_photo_attachment(i) + ','
        pprint(photos)
        bot.send_message(msg.user_id, f'{candidate[1]} {candidate[2]}\n{candidate[3]}\n', keyboard, photos)


    @bot.message_handler("Следующий")
    def next_candidate(msg):
        find_vk(msg)


    bot.infinity_polling()  # Бесконечный опрос ВК на изменения
