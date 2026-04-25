FROM python:3.12.4

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

RUN apt-get update \
  && apt-get install -y build-essential ffmpeg libsndfile1 \
  && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
  && rm -rf /var/lib/apt/lists/*

ENV HOME=/multilingual-vids-backend
WORKDIR $HOME

COPY ./backend/requirements ./requirements
RUN pip install --upgrade pip \
  && pip install -r ./requirements/prod.txt

COPY ./backend/src $HOME
COPY ./backend/compose/start.sh /start.sh
RUN sed -i 's/\r$//g' /start.sh \
  && chmod +x /start.sh
