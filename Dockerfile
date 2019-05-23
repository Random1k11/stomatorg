FROM python:3-alpine

RUN apk update && apk upgrade && pip3 install -U pip
RUN apk add --update alpine-sdk make gcc py-mysqldb libxslt-dev \
 	mariadb-dev libxml2-dev libc-dev openssl-dev libffi-dev zlib-dev openssh \
	&& rm -rf /var/cache/apk/*
#RUN apk --update add py-mysqldb


WORKDIR /app

COPY . /app

RUN pip3 --no-cache-dir install -r requirements.txt

ENTRYPOINT ["python3"]
CMD ['stomatorg.py']
