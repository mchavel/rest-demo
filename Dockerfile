FROM python:3-alpine

# Create app directory
WORKDIR /app

# Install app dependencies
COPY requirements.txt ./

RUN pip install -r requirements.txt

# Bundle app source
COPY ./app.py .
COPY ./api_db.py .
COPY ./config.ini .
COPY ./albums.json .

# Run as non-root user
USER guest

EXPOSE 5000
CMD [ "flask", "run", "--host", "0.0.0.0", "--port", "5000" ]
