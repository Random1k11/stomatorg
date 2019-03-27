# -*- coding: utf-8 -*-
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound
import mysql.connector
import datetime
import logging
from config import Config


logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)
formatter = logging.Formatter('[%(asctime)s, level: %(levelname)s, file: %(name)s, function: %(funcName)s], message: %(message)s')
file_handler = logging.FileHandler('logs/database.log', mode='w')
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.ERROR)
logger.addHandler(file_handler)



engine = create_engine('mysql+mysqlconnector://{0}:{1}@{2}/{3}'.format(Config.user, Config.passwd, Config.host, Config.database))
engine.execute("CREATE DATABASE IF NOT EXISTS " + Config.database) #create db
engine.execute("USE " + Config.database) # select new db

Base = declarative_base()

Session = sessionmaker(bind=engine)
Session = sessionmaker()
Session.configure(bind=engine)
Session.configure(bind=engine)
session = Session()



class Product(Base):

    __tablename__ = 'Product'

    id = Column(Integer, primary_key=True)
    title = Column(String(300))
    description = Column(Text)
    price = Column(Integer)
    producer = Column(String(100))
    articul = Column(String(100))
    code = Column(Integer)
    photo = Column(Text)
    subsection = Column(String(100))
    href = Column(String(1000))
    created_date = Column(DateTime, default=datetime.datetime.now)

    def __repr__(self):
        return "<Product(title= '%s')>" % self.title

class HistoryProduct(Base):

    __tablename__ = 'History_Product'

    id = Column(Integer)
    title = Column(String(300))
    description = Column(Text)
    price = Column(Integer)
    producer = Column(String(100))
    articul = Column(String(100))
    code = Column(Integer)
    photo = Column(Text)
    subsection = Column(String(100))
    href = Column(String(1000))
    created_date = Column(DateTime, default=datetime.datetime.now,  primary_key=True)

    def __repr__(self):
        return "<History_Product(title= '%s')>" % self.title

Base.metadata.create_all(engine)


def insert_row_to_current_database(result):
    try:
        p = Product(title=result[0], description=result[1], price=result[2], producer=result[3], articul=result[4],
                    code=result[5], photo=result[6], subsection=result[7], href=result[8])
        session.add(p)
        session.commit()
    except:
        logger.exception('Ошибка при записи нового товара в БД: ' + p)
        session.rollback()
        p = Product(title=result[0], description=result[1], price=result[2], producer=result[3], articul=result[4],
                    code=result[5], photo=result[6], subsection=result[7], href=result[8])
        session.add(p)
        session.commit()


def get_price_from_databse(href):
    try:
        p = session.query(Product).filter(Product.href == href).one()
        return p.price
    except:
        logger.exception('Ошибка при получении информации о цене товара: ' + href)
        session.rollback()
        try:
            p = session.query(Product).filter(Product.href == href).one()
            return p.price
        except:
            pass



def check_existence_row_in_db(href):
    try:
        p = session.query(Product).filter(Product.href == href).scalar()
        return p
    except:
        logger.exception('Ошибка при проверки на существование в БД ' + href)
        session.rollback()
        p = session.query(Product).filter(Product.href == href).scalar()
        return p

def update_price(href, price):
    try:
        session.query(Product).filter(Product.href == href).update(dict(price=price, created_date=datetime.datetime.now()))
        session.commit()
    except:
        logger.exception('Ошибка при обновлении цены товара ' + href)
        session.rollback()
        session.query(Product).filter(Product.href == href).update(dict(price=price, created_date=datetime.datetime.now()))
        session.commit()



def insert_row_to_history_database(href):
    try:
        session.execute('INSERT INTO History_Product (SELECT * FROM Product WHERE href="' + href + '");')
        session.commit()
    except:
        logger.exception('Ошибка при записи товара в историческую БД: ' + href)
        session.rollback()
        session.execute('INSERT INTO History_Product (SELECT * FROM Product WHERE href="' + href + '");')
        session.commit()


def get_all_href():
    try:
        p = session.query(Product).all()
        all_href_in_db = [i.href for i in p]
    except:
        logger.exception('Ошибка при получении ссылок на товары из БД')
        session.rollback()
        p = session.query(Product).all()
        all_href_in_db = [i.href for i in p]
        return all_href_in_db
    return all_href_in_db


def delete_from_db(href):
    try:
        p = session.query(Product).filter(Product.href == href).one()
        session.delete(p)
        session.commit()
    except:
        logger.exception('Ошибка при удалении товара из основной БД: ' + href)
        session.rollback()
        p = session.query(Product).filter(Product.href == href).one()
        session.delete(p)
        session.commit()
