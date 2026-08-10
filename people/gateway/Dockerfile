FROM python

ADD . ./opt/people/gateway
ADD . ./opt/people/requirements.txt

WORKDIR /opt/people/gateway

RUN pip install -r requirements.txt

EXPOSE 5002

CMD ["python", "gateway.py"]