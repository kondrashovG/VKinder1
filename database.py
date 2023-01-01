import json
import psycopg2
from psycopg2 import OperationalError
import datetime


class VKinderDB:
    def __init__(self, database='VKinder', user='postgres', password=''):
        """
        :param database: имя БД
        :param user: имя для доступа к БД
        :param password: пароль
        Здесь создается БД.
        Краткое описание таблиц и полей:

        humans - содержит информацию о пользователях чат-бота и отобранных кандидатах:
            vkid - id из VK (первичный ключ)
            name - имя
            surname - фамилия
            bithday - дата рождения
            city - город
            gender - пол (True - М, False - Ж)
            photo - содержит список ссылок на фото.
                    типа [photo1, photo2, photo3].
        list - здесь формируются списки избранных и отвергнутых (черный список):
            owner_id - id клиента чат-бота из VK,
                        в humans обязательно присутствует уникальная запись, где vkid == owner_id
            vkid - id выбранного кандидата из VK,
                        в humans обязательно присутствует уникальная запись, где vkid == vkid
            sel_ign - содержит True (означает, что это список "Избранное") или
                        False (означает, что это "Черный" список)
            (owner_id, vkid) - первичный ключ таблицы
        """
        self.connect = psycopg2.connect(database=database, user=user, password=password)
        with self.connect.cursor() as cur:
            try:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS humans (
                        vkid int4 PRIMARY KEY,      
                        name varchar NOT NULL,
                        surname varchar NOT NULL,
                        birthday date NOT NULL,
                        city varchar NOT NULL,
                        gender bool NOT NULL,
                        photo varchar[]
                    );
                    CREATE TABLE IF NOT EXISTS list (
                        owner_id int4 REFERENCES humans(vkid),
                        vkid int4 REFERENCES humans(vkid),
                        sel_ign bool NOT NULL,
                        CONSTRAINT list_pk PRIMARY KEY (owner_id, vkid)
                    );
                    """)
                self.connect.commit()
                print('БД создана успешно', database)
            except OperationalError as e:
                print(f"Произошла ошибка '{e}'")

    def insert_client(self, owner_id: int, name: str, surname: str, birthday: datetime, city: str, gender: bool,
                      photo: json):
        """
        :param owner_id: id клиента чат-бота из VK
        :param name: имя клиента чат-бота из VK
        :param surname: фамилия клиента чат-бота из VK
        :param birthday: дата рождения клиента чат-бота из VK
        :param city: город клиента чат-бота из VK
        :param gender: пол клиента чат-бота из VK (True - М, False - Ж)
        :param photo: содержит список ссылок на фото. типа [photo1, photo2, photo3].
                        Но может быть и другим в формате json
        :return: nothing

        Метод заносит в БД клиента чат-бота. По замыслу вызывается при каждом входе клиента в чат. Если информация в БД
        о текущем клиенте уже есть, она обновляется (бывает клиенты меняют информацию о себе, добавляют фото).
        Параметр photo м.б. пустым.
        """
        with self.connect.cursor() as cur:
            try:
                cur.execute(
                    """INSERT INTO 
                        humans ( 
                            vkid,
                            name,
                            surname,
                            birthday,
                            city,
                            gender,
                            photo) 
                    VALUES
                        (%s, %s, %s, %s, %s, %s, %s) 
                    ON CONFLICT ON CONSTRAINT humans_pkey DO 
                    UPDATE SET
                        name=%s, 
                        surname=%s, 
                        birthday=%s, 
                        city=%s, 
                        gender=%s,
                        photo=%s
                    WHERE humans.vkid=%s;""", (owner_id, name, surname, birthday, city, gender, photo,
                                               name, surname, birthday, city, gender, photo, owner_id))
                self.connect.commit()
                print(f'Клиент {name} {surname} успешно добавлен')
            except OperationalError as e:
                print(f"Произошла ошибка '{e}'")
#
    def insert_selected(self, owner_id: int, vk_id: int, sel_ign: bool,
                        name, surname, birthday, city, gender, photo):
        """
        :param owner_id: id клиента чат-бота из VK
        :param vk_id: id отобранного кандидата из VK
        :param sel_ign: содержит True (означает, что это список "Избранное") или
                        False (означает, что это "Черный" список)
        :param name: имя кандидата из VK
        :param surname: фамилия кандидата из VK
        :param birthday: дата рождения кандидата из VK
        :param city: город кандидата из VK
        :param gender: пол кандидата из VK (True - М, False - Ж)
        :param photo: содержит список ссылок на фото. типа [photo1, photo2, photo3].
                        Но может быть и другим в формате json. может быть пустым, если нет фоток
        :return: nothing

        Метод вызывается, чтобы добавить кандидата в список избранных (sel_ign == True) или в черный список
        (sel_ign == False). В таблицу list вносится id кандидата из VK. Вся остальная информация
        (имя, фамилия, дата рождения, город, пол и ссылки на фото) вносится в таблицу Humans. Если запись о кандидате
        уже есть в Humans (другие пользователи чат-бота уже могли добавить этого кандидата), то эта информация
        обновляется (мало ли, что-то могло измениться).
        """
        with self.connect.cursor() as cur:
            try:
                cur.execute(
                    """
                    INSERT
                        INTO humans (
                            vkid,
                            name,
                            surname,
                            birthday,
                            city,
                            gender, 
                            photo)
                    VALUES
                        (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT ON CONSTRAINT humans_pkey DO 
                    UPDATE SET
                        name=%s, 
                        surname=%s, 
                        birthday=%s, 
                        city=%s, 
                        gender=%s, 
                        photo=%s
                    WHERE humans.vkid=%s;
                    INSERT 
                        INTO list (
                            owner_id,
                            vkid,
                            sel_ign)
                    VALUES
                        (%s, %s, %s)
                    ON CONFLICT ON CONSTRAINT list_pk DO
                    UPDATE SET
                        sel_ign=%s
                    WHERE list.owner_id=%s AND list.vkid=%s
                    """, (vk_id, name, surname, birthday, city, gender, photo, name, surname, birthday, city, gender,
                          photo, vk_id, owner_id, vk_id, sel_ign, sel_ign, owner_id, vk_id))
                self.connect.commit()
                print(f'Выбранная запись {name} {surname} успешно добавлена')
            except OperationalError as e:
                print(f"Произошла ошибка '{e}'")

    def delete_from_list(self, owner_id: int, vk_id: int):
        """
        :param owner_id: id клиента чат-бота из VK
        :param vk_id: id кандидата из VK
        :return: nothing

        Метод вызываем, чтобы удалить кандидата из списка "Избранное" или из "Черного" списка (вдруг юзер погорячился,
        внес знаком(ую,ого) в черный список, а потом захотел это исправить).
        """
        with self.connect.cursor() as cur:
            try:
                cur.execute(
                    """                  
                        DELETE FROM list
                        WHERE owner_id=%s AND vkid=%s;
                        DELETE FROM humans
                        WHERE (SELECT count(vkid) FROM list WHERE vkid=%s) = 0 AND vkid=%s               
                    """, (owner_id, vk_id, vk_id, vk_id))
                self.connect.commit()
                print(f'Выбранная запись {owner_id} {vk_id} успешно удалена')
            except OperationalError as e:
                print(f"Произошла ошибка '{e}'")

    def favorites_list(self, owner_id, black_or_white):
        """
        :param owner_id: id клиента чат-бота из VK
        :param black_or_white: содержит True (означает, что это список "Избранное") или
                                False (означает, что это "Черный" список)
        :return: возвращает список кандидатов [(id, name, surname, birthday, city, photo),...]
        Метод возвращает всю информация из списка "Избранных" или из "Черного" списка.
        """
        with self.connect.cursor() as cur:
            try:
                cur.execute(
                    """                  
                        SELECT h.vkid, name, surname, birthday, city, photo FROM humans as h, list as l
                        WHERE owner_id=%s AND sel_ign = %s AND h.vkid=l.vkid             
                    """, (owner_id, black_or_white))
                self.connect.commit()
                return cur.fetchall()
            except OperationalError as e:
                print(f"Произошла ошибка '{e}'")

    def close_connect(self):
        self.connect.close()
