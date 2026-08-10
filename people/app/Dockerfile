FROM python

ADD . ./opt/people/app
ADD . ./opt/people/requirements.txt

WORKDIR /opt/people/app

RUN pip install -r requirements.txt

EXPOSE 5000

CMD ["python", "app.py"]