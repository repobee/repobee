FROM python:3.8-alpine

RUN apk update
RUN apk add git bash

RUN addgroup -S repobee && adduser -S repobee -G repobee
USER repobee
ENV PATH=${PATH}:/home/repobee/.repobee/bin

COPY . /home/repobee/repobee

RUN mkdir -p /home/repobee/.config/repobee
RUN mkdir /home/repobee/workdir
WORKDIR /home/repobee/workdir

RUN bash ~/repobee/scripts/install.sh ~/repobee
