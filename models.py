# -*- coding: utf-8 -*-
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound
import datetime
import logging
from config import Config

# from sqlalchemy import exc
# from sqlalchemy import event
# from sqlalchemy.pool import Pool
#
#
# @event.listens_for(Pool, "checkout")
# def ping_connection(dbapi_connection, connection_record, connection_proxy):
#     cursor = dbapi_connection.cursor()
#     try:
#         cursor.execute("SELECT 1")
#     except:
#         raise exc.DisconnectionError()
#     cursor.close()



logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)
formatter = logging.Formatter('[%(asctime)s, level: %(levelname)s, file: %(name)s, function: %(funcName)s], message: %(message)s')

engine = create_engine('mysql://{0}:{1}@{2}/{3}?charset=utf8'.format(Config.user, Config.passwd, Config.host, Config.database), echo_pool=True)
engine.execute("USE " + Config.database) # select new db

# Session = sessionmaker(bind=engine)
# Session.configure(bind=engine)
# session = Session()

Base = declarative_base()


class Product(Base):

    __tablename__ = 'Product'

    id = Column(Integer, primary_key=True)
    title = Column(Text)
    description = Column(Text)
    price = Column(Integer)
    producer = Column(String(500))
    articul = Column(String(500))
    code = Column(Integer)
    photo = Column(Text)
    subsection = Column(Text)
    href = Column(Text)
    created_date = Column(DateTime, default=datetime.datetime.now)

    def __repr__(self):
        return "<Product(title= '%s')>" % self.title


class HistoryProduct(Base):

    __tablename__ = 'History_Product'

    id = Column(Integer)
    title = Column(String(500))
    description = Column(Text)
    price = Column(Integer)
    producer = Column(String(500))
    articul = Column(String(500))
    code = Column(Integer)
    photo = Column(Text)
    subsection = Column(String(500))
    href = Column(String(1000))
    created_date = Column(DateTime, default=datetime.datetime.now,  primary_key=True)

    def __repr__(self):
        return "<History_Product(title= '%s')>" % self.title


Base.metadata.create_all(engine)


def insert_row_to_current_database(session, result):
    # p = Product(title=result[0].encode('utf-8'), description=result[1].encode('utf-8'), price=result[2].encode('utf-8'), producer=result[3].encode('utf-8'), articul=result[4].encode('utf-8'),
    #             code=result[5].encode('utf-8'), photo=result[6].encode('utf-8'), subsection=result[7].encode('utf-8'), href=result[8].encode('utf-8'))

    p = Product(title=result[0], description=result[1], price=result[2], producer=result[3], articul=result[4],
                code=result[5], photo=result[6], subsection=result[7], href=result[8])
    session.add(p)
    session.commit()


def get_price_from_databse(session, href):
    return session.query(Product).filter(Product.href == href).first().price


def check_existence_row_in_db(session, href):
    return session.query(Product).filter(Product.href == href).first()


def update_price(session, href, price):
    session.query(Product).filter(Product.href == href).update(dict(price=price, created_date=datetime.datetime.now()))
    session.commit()


def insert_row_to_history_database(session, href):
    session.execute('INSERT INTO History_Product (SELECT * FROM Product WHERE href="' + href + '");')
    session.commit()


def get_all_href():
    try:
        p = session.query(Product).all()
        all_href_in_db = [i.href for i in p]
        return all_href_in_db
    except:
        logger.exception('Ошибка при получении ссылок на товары из БД')
        session.rollback()
        p = session.query(Product).all()
        all_href_in_db = [i.href for i in p]
        return all_href_in_db


def delete_from_db(href):
    try:
        p = session.query(Product).filter(Product.href == href).one()
        session.delete(p)
        session.commit()
    except:
        logger.exception('Ошибка при удалении товара из основной БД: ' + str(href))
        session.rollback()
        p = session.query(Product).filter(Product.href == href).one()
        session.delete(p)
        session.commit()
