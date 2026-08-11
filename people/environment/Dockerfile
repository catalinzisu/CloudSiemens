FROM python

WORKDIR /opt/people/environment

# install dependencies first for better cache
COPY requirements.txt ./
RUN pip install -r requirements.txt

# copy the application code
COPY . ./

EXPOSE 5003

CMD ["python", "environment.py"]