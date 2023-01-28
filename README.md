## Docker System Version

Image version

-   Python version `3.11-buster`

Used Library Version

-   pdfplumber version `1.5.2`
-   pandas version `0.7.6`


## Installation

Create docker image (Recommanded)
```console
$ docker build -t bs-parser .
```

Run in local

```console
# Need to install pandas and pdfplumber first
$ pip install pandas==1.5.2
$ pip install pdfplumber==0.7.6
```

## How to use

Docker
```console
$ docker run --rm -it -v ${pwd}:/src -w /src bs-parser 
```

Local
```console
$ python3 app.py
```


