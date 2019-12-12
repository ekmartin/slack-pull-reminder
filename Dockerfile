FROM python:3.6.5-alpine3.7

WORKDIR /app

RUN apk add --no-cache -q openssl-dev libffi-dev build-base \
    && pip install -q setuptools

COPY . .
RUN python setup.py install

CMD ["slack-pull-reminder"]