FROM python

WORKDIR /opt/people

# install dependencies first for better cache
COPY app/requirements.txt ./app/
RUN pip install -r app/requirements.txt

# copy the HTML files and directories needed by the app
COPY person.html index.html error.html ./
COPY doom/ ./doom/

# copy the application code
COPY app/ ./app/

WORKDIR /opt/people/app
EXPOSE 5000

CMD ["python", "app.py"]