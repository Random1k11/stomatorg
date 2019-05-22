# -*- coding: utf8 -*-
from bs4 import BeautifulSoup
import re
import logging
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from config import Config
from models import Product, insert_row_to_current_database, get_price_from_databse, update_price,\
                    check_existence_row_in_db, insert_row_to_history_database, get_all_href, delete_from_db
import progressbar
import multiprocessing
from sqlalchemy.exc import IntegrityError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)
formatter = logging.Formatter('[%(asctime)s, level: %(levelname)s, file: %(name)s, function: %(funcName)s], message: %(message)s')
file_handler = logging.FileHandler('stomatorg.log', mode='w')
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



class StomatorgSpider():

    name = 'stomatorg'
    start_url = Config.section_link


    def __init__(self):
        self.browser = webdriver.Chrome(options=options)
        # self.session = session
        engine = create_engine('mysql://{0}:{1}@{2}/{3}?charset=utf8'.format(Config.user, Config.passwd, Config.host, Config.database), echo_pool=True)
        engine.execute("USE " + Config.database) # select new db
        Session = sessionmaker(bind=engine)
        Session.configure(bind=engine)
        self.session = Session()


    def get_sections(self):
        self.browser.get(self.start_url)
        try:
            Elem = WebDriverWait(self.browser, 25).until(EC.presence_of_element_located((By.XPATH, '//*[@id="mobile-menu-burger"]/div/ul/li/a')))
        except TimeoutException:
            logger.exception('Элемент не загрузился')
        sections = [i.get_attribute('href') for i in self.browser.find_elements_by_xpath('//*[@id="mobile-menu-burger"]/div/ul/li/a')]
        self.browser.quit()
        return sections


    def parse(self, sections, start, end):
        sections_links = sections[start:end]
        bar = progressbar.ProgressBar()
        for i in bar(range(len(sections_links))):
            self.browser.get(sections_links[i])
            self.get_product_page(sections_links[i])


    def get_product_page(self, url_section):
        for url_product in self.get_inks_to_products():
            self.browser.get(url_product)
            info_product = self.parse_product()
        self.browser.get(url_section)
        try:
            Elem = WebDriverWait(self.browser, 25).until(EC.presence_of_element_located((By.XPATH, '//a[@id="navigation_1_next_page"]')))
            next_page_url = self.browser.find_element_by_xpath('//a[@id="navigation_1_next_page"]').get_attribute('href')
            self.browser.get(next_page_url)
            self.get_product_page(next_page_url)
        except TimeoutException:
            pass
        return info_product


    def get_inks_to_products(self):
        try:
            Elem = WebDriverWait(self.browser, 45).until(EC.presence_of_element_located((By.XPATH, '//div[@class="row products products_showcase "]')))
        except TimeoutException:
            logger.exception('Элемент не загрузился')
        list_products = self.browser.find_elements_by_xpath('//a[@class="js-compare-label js-detail_page_url"]')
        links = [i.get_attribute('href') for i in list_products]
        return links


    def parse_product(self):

        try:
            Elem = WebDriverWait(self.browser, 55).until(EC.presence_of_element_located((By.XPATH, '//div[@class="preview-wrap"]')))
        except TimeoutException:
            logger.exception('Элемент не загрузился')

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
            photo = ', '.join(photo)
            return photo

        def href():
            return self.browser.current_url

        result = [title(), description(), price(), producer(), artikul(), code(), photo(), subsection(), href()]
        logger.debug('=== Получена информация о товаре ===')
        return self.writing_data(result)


    def writing_data(self, result):
        try:
            if check_existence_row_in_db(self.session, result[8]) == None:
                logger.debug('=== Записываю в БД новый товар ===')
                insert_row_to_current_database(self.session, result)
            else:
                current_price = result[2]
                if int(current_price) != int(get_price_from_databse(self.session, result[8])):
                    logger.info('=== Цена товара изменилась ===')
                    try:
                        insert_row_to_history_database(self.session, result[8])
                        logger.info('=== Записываю в таблицу с историей ===')
                    except IntegrityError:
                        pass
                    update_price(self.session, result[8], current_price)
                    logger.info('=== Цена товара обновлена ===')
        except:
            self.session.rollback()
            raise
        finally:
            self.session.close()


def multi_threads(instances, links_on_sections):
    links = links_on_sections
    amount_sections = len(links_on_sections)
    number_of_sections_per_thread = amount_sections / 3

    t1 = round(number_of_sections_per_thread)
    t2 = round(number_of_sections_per_thread) + t1
    t3 = round(number_of_sections_per_thread) + t2


    thread_1 = multiprocessing.Process(
        target=instances[0].parse, args=(links, 0, t1)
    )
    thread_2 = multiprocessing.Process(
        target=instances[1].parse, args=(links, t1, t2)
    )
    thread_3 = multiprocessing.Process(
        target=instances[2].parse, args=(links, t2, t3)
    )

    thread_1.start()
    thread_2.start()
    thread_3.start()

    thread_1.join()
    thread_2.join()
    thread_3.join()




if  __name__ == "__main__":
    parser = StomatorgSpider()
    links = parser.get_sections()
    instances = [StomatorgSpider() for i in range(3)]
    multi_threads(instances, links)
