FROM node:alpine

RUN apk update \
    && apk add aria2 git \
    && mkdir /g-uploader

COPY . /g-uploader

ENV USER admin
ENV PASSWORD google

WORKDIR /g-uploader

RUN npm install && npm install -g forever && chmod +x setup.sh

EXPOSE 8080 6800

ENTRYPOINT ["/g-uploader/setup.sh"]
CMD ["--wait"]
