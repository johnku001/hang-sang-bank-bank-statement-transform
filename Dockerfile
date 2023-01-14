FROM python:3.11-buster
COPY app.py /src
RUN mkdir -p /csv_result
RUN mkdir -p /pdf_entry
RUN mkdir -p /finished_pdf
Run apt-get -y update
Run pip install pandas==1.5.2
Run pip install pdfplumber==0.7.6

CMD ["/usr/local/bin/python" ,"app.py" ,"--config", "/etc/config/config.json"]

