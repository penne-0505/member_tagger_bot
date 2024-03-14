# based python 3.12, pip install requirements
FROM python:3.12
WORKDIR /
COPY requirements.txt .
RUN pip install -r requirements.txt
CMD ["cd", "src", "&&", "python", "main.py"]