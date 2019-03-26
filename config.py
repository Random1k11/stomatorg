# -*- coding: utf-8 -*-

# Настройки базы данных и chromedriver


class Config:
    host="localhost"
    user="root"
    passwd="root"
    database="stomatorg"

    # Укажите путь к chromedriver
    path_to_chromedriver = 'chromedriver'

    section_link = 'https://shop.stomatorg.ru/catalog/stomatologicheskie_materialy_/'
