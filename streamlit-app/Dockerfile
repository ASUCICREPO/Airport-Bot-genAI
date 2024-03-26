FROM python:3.9-slim

WORKDIR /home/app

COPY requirements.txt .

RUN pip3 install -r requirements.txt

COPY app.py InvokeAgent.py log_setup.py ./

CMD ["streamlit", "run", "app.py"]