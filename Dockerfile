FROM python:3.11
RUN mkdir -p ./src
COPY app.py ./src
RUN mkdir -p ./src/csv_result
RUN mkdir -p ./src/pdf_entry
RUN mkdir -p ./src/finished_pdf
RUN apt-get -y update
RUN pip install pandas==1.5.2
RUN pip install pdfplumber==0.7.6


ENTRYPOINT ["python"]
CMD ["app.py"]

