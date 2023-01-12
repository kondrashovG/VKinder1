import vk_api
import requests
# from pprint import pprint
import time

# API_URL = 'https://api.vk.com/method/'


class VK:
    def __init__(self, user_token, API_URL):
        self.user_token = user_token
        self.API_URL = API_URL
        self.idnum = []

    def get_info(self, user_ids):
        method = 'users.get'
        url = self.API_URL + method
        params = {
            'user_ids': user_ids,
            'access_token': self.user_token,
            'fields': 'city, bdate, sex',
            'v': '5.131'
        }
        res = requests.get(url, params=params)
        response = res.json().get("response")
        print(response)
        return response

    def get_vk_photo(self, id):
        metod = 'photos.get'
        list_photos = {}
        params = {
            'access_token': self.user_token,
            'v': '5.131',
            'owner_id': id,
            'album_id': 'profile',
            'extended': '1'
        }
        response = requests.get(url=self.API_URL + metod, params=params)
        photo = response.json()
        if 'response' in photo.keys():
            for i in photo['response']['items']:
                index_size = 99
                for j in i['sizes']:
                    k = 'wzyrqpoxms'.find(j['type'])
                    if k < index_size:
                        index_size = k
                        max_url = j['url']
                list_photos.update([(i['likes']['count'], max_url)])
            return [sorted(list_photos.items(), key=lambda x: -x[0])[i][1] for i in range(min(3, len(list_photos)))]

    def search_users(self, sex, age_at, age_to, city):
        all_persons = []
        link_profile = 'https://vk.com/id'
        vk_ = vk_api.VkApi(token=self.user_token)
        response = vk_.method('users.search',
                              {'v': '5.89',
                               'sex': sex,
                               'age_from': age_at,
                               'age_to': age_to,
                               'city': city,
                               'fields': 'bdate'
                               })
        for element in response['items']:
            id = element['id']
            time.sleep(0.3)
            photo = self.get_vk_photo(id)
            if photo is not None:
                person = [
                    id,
                    element['first_name'],
                    element['last_name'],
                    element['bdate'],
                    link_profile + str(element['id']),
                    photo
                ]
                all_persons.append(person)
        return all_persons
