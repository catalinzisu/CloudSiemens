FROM python

ADD . ./opt/people/environment
ADD . ./opt/people/requirements.txt

WORKDIR /opt/people/environment

RUN pip install -r requirements.txt

EXPOSE 5003

CMD ["python", "environment.py"]