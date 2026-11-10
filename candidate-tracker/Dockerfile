FROM registry.access.redhat.com/ubi9/python-312:latest

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TRACKER_DATA_DIR=/tmp/workbooks

WORKDIR /opt/app-root/src/candidate-tracker

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# OpenShift runs containers as an arbitrary UID in group 0, so group needs the same access as the owner.
USER 0
RUN chgrp -R 0 /opt/app-root/src && chmod -R g=u /opt/app-root/src
USER 1001

EXPOSE 8080

CMD ["streamlit", "run", "app.py", "--server.port=8080", "--server.address=0.0.0.0", "--server.headless=true", "--browser.gatherUsageStats=false"]
