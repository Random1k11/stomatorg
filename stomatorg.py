# -*- coding: utf-8 -*-
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from bs4 import BeautifulSoup
import time
import mysql.connector
from database import Product, insert_row_to_current_database, get_price_from_databse, update_price,\
                    check_existence_row_in_db, insert_row_to_history_database, get_all_href, delete_from_db
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.exc import IntegrityError
import progressbar
import logging


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter('[%(asctime)s, level: %(levelname)s, file: %(name)s, function: %(funcName)s], message: %(message)s')
file_handler = logging.FileHandler('logs/stomatorg.log', mode='w')
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.ERROR)
stream_handler = logging.StreamHandler()
logger.addHandler(file_handler)
logger.addHandler(stream_handler)


options = Options()
options.add_argument('--headless')
options.add_argument("disable-extensions")
options.add_argument("disable-infobars")
options.add_argument("test-type")
options.add_argument("ignore-certificate-errors")
options.add_argument("--start-maximized")
options.add_argument('--no-sandbox')


class ParserStomatorg():


    def __init__(self, url):
        self.url = url
        self.browser = webdriver.Chrome(options=options)
        self.browser.get(self.url)

    def get_buttons_menu(self):
        try:
            Elem = WebDriverWait(self.browser, 55).until(EC.presence_of_element_located((By.XPATH, '//li[@class="nav-side__item level2 "]')))
        except TimeoutException:
            logger.exception('Элемент не загрузился')
        main_menu = [i.text for i in self.browser.find_elements_by_xpath('//*[@id="mobile-menu-burger"]/div/ul/li')]
        logger.debug('=== Полученно основное меню ===')
        return main_menu

    def links_on_products(self, link):
        try:
            Elem = WebDriverWait(self.browser, 55).until(EC.presence_of_element_located((By.XPATH, '//button[@id="dropdownMenuOutput"]')))
        except TimeoutException:
            logger.exception('Элемент не загрузился')
            self.browser.quit()
            self.__init__(link)
        soup = BeautifulSoup(self.browser.page_source, 'xml')
        sort_btn = (soup.findAll('span', class_='js-sorter-btn'))
        sort_btn = [i.text for i in sort_btn]
        try:
            if sort_btn[-1] != 'Все':
                self.browser.find_element_by_xpath('//button[@id="dropdownMenuOutput"]').click()
                # ActionChains(self.browser).move_to_element(self.browser.find_element_by_xpath('//button[@id="dropdownMenuOutput"]')).click().perform()
                time.sleep(7) # all products selected
                self.browser.find_element_by_xpath('//*[@id="composite_sorter"]/div[3]/div/ul/li[7]/a').click()
                # ActionChains(self.browser).move_to_element(self.browser.find_element_by_xpath('//*[@id="composite_sorter"]/div[3]/div/ul/li[7]/a')).click().perform()
                time.sleep(15)
        except IndexError:
            pass
        list_products = self.browser.find_elements_by_xpath('//a[@class="js-compare-label js-detail_page_url"]')
        links = [i.get_attribute('href') for i in list_products]
        logger.debug('=== Полученны ссылки на товары ===')
        return links

    def get_sections_page(self, page):
        self.browser.get(page)

    def get_info_from_site(self, page, main_section):

        self.browser.get(page)
        try:
            Elem = WebDriverWait(self.browser, 55).until(EC.presence_of_element_located((By.XPATH, '//div[@class="preview-wrap"]')))
        except TimeoutException:
            print('время вышло')
        time.sleep(5)

        def subsection():
            return self.browser.find_elements_by_xpath('//a[@itemprop="item"]')[-1].text

        def title():
            return self.browser.find_element_by_xpath('//div[@class="page-title  "]/h1').text.strip()

        def description():
            return self.browser.find_element_by_xpath('//div[@class="product-announce"]').text.strip()

        def price():
            soup = BeautifulSoup(self.browser.page_source, 'lxml')
            price = (soup.find('div', class_='prices__values').text)
            price = price.split('руб.')
            price = [i.replace('\n', '') for i in price if i.replace('\n', '') != '']
            if len(price) > 1:
                return price[-1].replace(' ', '').strip()
            else:
                return price[0].replace(' ', '').strip()

        def producer():
            soup = BeautifulSoup(self.browser.page_source, 'xml')
            for i in soup.findAll('span', class_='js-article'):
                if 'Производитель' in i.parent.text:
                    return i.parent.text.replace('Производитель: ', '').strip()
            return 'Не указан Производитель'

        def artikul():
            soup = BeautifulSoup(self.browser.page_source, 'xml')
            for i in soup.findAll('span', class_='js-article'):
                if 'Артикул' in i.parent.text:
                    return i.parent.text.replace('Артикул:', '').strip()
            return 'Не указан артикул'

        def code():
            soup = BeautifulSoup(self.browser.page_source, 'xml')
            for i in soup.findAll('span', class_='js-article'):
                if 'код' in i.parent.text:
                    return i.parent.text.replace('код:', '').strip()
            return 'Не указан код'

        def photo():
            photo = [i.get_attribute('src') for i in self.browser.find_elements_by_xpath('//img[@class="preview"]')]
            photo = ', '.join(photo[0])
            return photo

        def href():
            return self.browser.current_url


        result = [title(), description(), price(), producer(), artikul(), code(), photo()[0][0], main_section, subsection(), href()]
        logger.debug('=== Получена информация о товаре ===')
        return result


    def get_links_from_section(self):
        bar = progressbar.ProgressBar()
        main_section = self.get_buttons_menu()
        for btn in bar(range(len(main_section))): # главные разделы
            self.browser.find_element_by_xpath('//*[@id="mobile-menu-burger"]/div/ul/li/*[contains(string(), "{}")]'.format(main_section[btn])).click()
            time.sleep(15)
            links_sections = [i.get_attribute('href') for i in self.browser.find_elements_by_xpath('//ul[@class="nav-side__submenu nav-side__lvl2 lvl2 collapse in"]/li/a')]
            for link in links_sections[:]: # подразделы
                time.sleep(2)
                self.get_sections_page(link)
                links = self.links_on_products(link)
        return len(links)

    def checking_current_products(self):
        """ Проверяет актуальность товаров,
        если товара больше нет удаляет из основной таблицы и записывает в таблицу с историей """
        links = self.get_links_from_section()
        for i in get_all_href():
            if i not in links:
                logger.info(i)
                try:
                    insert_row_to_history_database(i)
                    logger.info('=== Товара нет в продаже, записываю в таблицу с историей ===')
                except IntegrityError:
                    pass
                try:
                    delete_from_db(i)
                    logger.info('=== Удаляю товар из основной таблицы ===')
                except NoResultFound:
                    pass



def main_loop():

    for btn in p.get_buttons_menu(): # главные разделы
        p.browser.find_element_by_xpath('//*[@id="mobile-menu-burger"]/div/ul/li/*[contains(string(), "{}")]'.format(btn)).click()
        time.sleep(15)
        links_sections = [i.get_attribute('href') for i in p.browser.find_elements_by_xpath('//ul[@class="nav-side__submenu nav-side__lvl2 lvl2 collapse in"]/li/a')]
        for link in links_sections[:]: # подразделы
            time.sleep(2)
            p.get_sections_page(link)
            links = p.links_on_products(link)
            bar = progressbar.ProgressBar()
            for link_on_product in bar(range(len(links))): # Ссылки на товары
                result = p.get_info_from_site(links[link_on_product], btn)
                if check_existence_row_in_db(links[link_on_product]) == None:
                    logger.debug('=== Записываю в БД новый товар ===')
                    insert_row_to_current_database(result)
                else:
                    current_price = result[2]
                    if int(current_price) != int(get_price_from_databse(links[link_on_product])):
                        logger.info('=== Цена товара изменилась ===')
                        try:
                            insert_row_to_history_database(links[link_on_product])
                            logger.info('=== Записываю в таблицу с историей ===')
                        except IntegrityError:
                            pass
                        update_price(links[link_on_product], current_price)
                        logger.info('=== Цена товара обновлена ===')
            logger.info('=== Завершен сбор информации по разделу: ' + str(result[-2]) + ' ===')



p = ParserStomatorg('https://shop.stomatorg.ru/catalog/stomatologicheskie_materialy_/')

if __name__ == '__main__':
    main_loop()
