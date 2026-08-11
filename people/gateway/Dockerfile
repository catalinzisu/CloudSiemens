FROM python

WORKDIR /opt/people/gateway

# install dependencies first for better cache
COPY requirements.txt ./
RUN pip install -r requirements.txt

# copy the application code
COPY . ./

EXPOSE 5002

CMD ["python", "gateway.py"]