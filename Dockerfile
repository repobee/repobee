FROM python:3.12-alpine

ARG SOURCE_DIRECTORY=/home/repobee/repobee/

RUN apk update

# dependencies for RepoBee
RUN apk add git bash

# dependencies for cffi, which at the time of writing is required by PyGithub==1.55
RUN apk add gcc libffi-dev libc-dev linux-headers

RUN addgroup -S repobee -g 1000 && adduser -S repobee -G repobee -u 1000

RUN mkdir "$SOURCE_DIRECTORY"
COPY src "$SOURCE_DIRECTORY/src"
COPY setup.py README.md scripts/install.sh "$SOURCE_DIRECTORY"

RUN chown -R repobee:repobee /home/repobee

USER repobee
RUN mkdir -p ~/.config/repobee
RUN mkdir ~/workdir
ENV PATH=${PATH}:/home/repobee/.repobee/bin
WORKDIR /home/repobee/workdir

RUN bash "$SOURCE_DIRECTORY/install.sh" ~/repobee
RUN echo "source $HOME/.repobee/completion/bash_completion.sh" >> "$HOME/.bashrc"

RUN rm -rf "$SOURCE_DIRECTORY"
