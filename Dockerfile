FROM python:3.8-alpine

RUN apk update
RUN apk add git bash

RUN addgroup -S repobee -g 1000 && adduser -S repobee -G repobee -u 1000

COPY . /home/repobee/repobee
RUN chown -R repobee:repobee /home/repobee

USER repobee
RUN mkdir -p /home/repobee/.config/repobee
RUN mkdir /home/repobee/workdir
ENV PATH=${PATH}:/home/repobee/.repobee/bin
WORKDIR /home/repobee/workdir

RUN bash ~/repobee/scripts/install.sh ~/repobee
RUN echo "source $HOME/.repobee/completion/bash_completion.sh" >> "$HOME/.bashrc"

RUN rm -rf ~/repobee
