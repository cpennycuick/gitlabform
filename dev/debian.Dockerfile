FROM python:3.9-buster
RUN apt-get update \
    && apt-get install -y pandoc \
    && apt-get clean
COPY . /gitlabform
RUN cd gitlabform && python setup.py develop
WORKDIR /config
