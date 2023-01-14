FROM python:3.11-buster
COPY app.py /src
RUN mkdir -p /csv_result
RUN mkdir -p /pdf_entry
RUN mkdir -p /finished_pdf
RUN apt-get -y update
RUN pip install pandas==1.5.2
RUN pip install pdfplumber==0.7.6


ENTRYPOINT [ "/bin/bash", "-l", "-c" ]
CMD ["python3" ,"app.py"]

