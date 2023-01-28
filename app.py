import pandas as pd
import pdfplumber
import datetime
import os
import json

TO_BE_PROCESS_FOLDER_PATH = "./pdf_entry/"
PROCESSED_FOLDER_PATH = "./finished_pdf/"
OUTPUT_FILE_CSV_PATH = "./csv_result/"
OUTPUT_FILE_JSON_PATH = "result.json"
RECORD_TABLE_EXTRACT_SETTING = {
    "vertical_strategy": "lines", 
    "horizontal_strategy": "text",
    "intersection_tolerance": 2,
    "keep_blank_chars": False,
    "join_y_tolerance":5,
}
ACCOUNT_INFO_EXTRACT_SETTING = {
    "vertical_strategy": "text", 
    "horizontal_strategy": "text",
    "intersection_tolerance": 2,
    "keep_blank_chars": False,
    "join_y_tolerance":5,
}

class RawRecord:
    def __init__(self, date: str, transaction_details: str, deposit: float, withdrawal: float, balance: float, line_number: int, page_number: int,  file_name: str , release_statement_date: str, account_number: str, account_type: str):
        self.date = date
        self.transformed_date =  str(datetime.datetime.strptime(date, "%d %b %Y"))
        self.transaction_details = transaction_details
        self.deposit = deposit
        self.withdrawal = withdrawal
        self.balance = balance
        self.line_number = line_number
        self.page_number = page_number
        self.file_name = file_name
        self.release_statement_date = release_statement_date
        self.account_number = account_number
        self.account_type = account_type
        
class AccountRecord:
     def __init__(self, statement_date: str, account_number: str, account_type: str, account_summary: pd.DataFrame, account_entries: pd.DataFrame, page_number: list[int]):
        self.statement_date = statement_date
        self.account_number = account_number
        self.account_type = account_type
        self.account_summary = account_summary
        self.account_entries = account_entries
        self.page_number = page_number

class PDFData: 
    def __init__(self, file_name: str, file_path: str, statement_date: str, account_number: str,  account_records:list[AccountRecord],number_of_page: int):
        self.file_name = file_name
        self.file_path = file_path
        self.statement_date = statement_date
        self.account_number = account_number
        self.account_records = account_records
        self.number_of_page = number_of_page

# return account number and statement_date
def get_account_info(pdf: pdfplumber.PDF): 
     df = pd.DataFrame(pdf.pages[0].extract_tables(RECORD_TABLE_EXTRACT_SETTING)[0])
     account_number = df.iloc[1][0].replace("Account Number", "").strip()
     statement_date = df.iloc[3][0].replace("Statement Date ", "").strip()
     return account_number, statement_date

def table_to_datatheme(table , statement_year, statement_month):
    if "Account Number" in table[1][0]:
        return None, "info"
    elif table[0][0] == "DEPOSIT SERVICES":
        return  to_summary_datatheme(table), "summary"
    elif table[1][0] == "Date":
        return to_record_datatheme(table, statement_year, statement_month), "record"
    elif table[0][0] == "FINANCIAL POSITION":
        return None, "financial"
    else:
        return None, "undefined"


def to_summary_datatheme(table: pdfplumber.PDF):
    df = pd.DataFrame(table[0:], columns= table[1:])
    df.columns = df.iloc[0]
    df = df.drop([0,1,2,3])
    return df

def to_record_datatheme (table: pdfplumber.table, statement_year: str, statement_month:str):
    df = pd.DataFrame(table[1:], columns= table[1:])
    try:
        df.columns = df.iloc[0]
        df = df.drop([0,1])
        date = ""
        removeIndex = []
        for index, row in df.iterrows():
            if row["Deposit"] == "" and row["Withdrawal"] == "" and row["Balance"] == "":    
                  df.loc[index + 1, "Transaction Details"] = df.loc[index, "Transaction Details"] + " " + df.loc[index + 1, "Transaction Details"]
                  removeIndex.append(index)
            if row["Date"] == "":
                df.loc[index, "Date"] = date
            else:
                date = row["Date"]
            if "Dec" in date and "Jan" in statement_month :
                df.loc[index, "Date"] = date + " " + str(int(statement_year)-1)
            else:
                df.loc[index, "Date"] = date + " " + statement_year

        df = df.drop(removeIndex)
    except Exception as e:
        raise Exception("Cannot transform record to datetheme of row " + index + ": " + str(e))
    return df

def get_all_account_records(pdf: pdfplumber.PDF, statement_date: str):
    statement_year = statement_date.split()[2]
    statement_month = statement_date.split()[1]
    account_records = list()
    page_number = list()
    is_prev_records_end = True
    tmp_account_entries = None
    account_entries = pd.DataFrame()
    account_summary = pd.DataFrame()
    for page in pdf.pages:
        tables =  page.extract_tables(RECORD_TABLE_EXTRACT_SETTING)

        for table in tables:
            df, type = table_to_datatheme(table, statement_year, statement_month)
            if type == "summary":
                account_summary = df
            elif type == "record":
                if df["Transaction Details"].str.contains("C/F BALANCE").any() == False:
                    if tmp_account_entries != None: 
                        tmp_account_entries = pd.concat([tmp_account_entries, df])
                    else:
                        tmp_account_entries = df
                    is_prev_records_end = False
                else :
                    if df["Transaction Details"].str.contains("C/F BALANCE").any() == True and is_prev_records_end == False:
                        datafield = pd.concat([tmp_account_entries, df])
                        account_entries = datafield
                        is_prev_records_end = True
                        tmp_account_entries = None
                        page_number.append(page.page_number)
                    else:
                        account_entries = df
                        is_prev_records_end = True
                        tmp_account_entries = None
                        page_number.append(page.page_number)

            
            if not account_entries.empty and not account_summary.empty:
                account_records.append(AccountRecord(statement_date, account_summary.iloc[0]["Account Number"], account_summary.iloc[0]["DEPOSIT SERVICES"], account_summary, account_entries, page_number))
                account_entries = pd.DataFrame()
                account_summary = pd.DataFrame()
                page_number = list()
    
    return account_records       

def account_record_to_raw_records(file_path: str, account_record: AccountRecord):
    account_entries = account_record.account_entries
    statement_date = account_record.statement_date
    raw_records = []
    file_name = os.path.basename(file_path)

    for index, row in account_entries.iterrows():
        date = None
        if row["Date"] == "":
            date = statement_date
        else:
            date = row["Date"]
        raw_records.append(RawRecord(
            date, 
            ' '.join(row["Transaction Details"].split()), 
            row["Deposit"], 
            row["Withdrawal"], 
            row["Balance"], 
            index,
            account_record.page_number,
            file_name,
            account_record.statement_date,
            account_record.account_number.strip(),
            account_record.account_type.strip()
            ))
    return raw_records

def get_pdf_data(file_path: str):
    try:
        file_name = os.path.basename(file_path)
        pdf = pdfplumber.open(file_path)
    except Exception as e:
        raise Exception("Cannot open file: " + str(e))
    else:
        account_number, statement_date = get_account_info(pdf)
        account_records = get_all_account_records(pdf, statement_date)
        os.rename(file_path, PROCESSED_FOLDER_PATH + file_name)
        return PDFData(file_name, file_path,statement_date, account_number,  account_records, len(pdf.pages))


def account_record_to_csv(account_record: AccountRecord):
    statement_year = account_record.statement_date.split()[2]
    statement_month = datetime.datetime.strptime(account_record.statement_date.split()[1], "%b").strftime("%m")
    account_entries = account_record.account_entries
    try:
        filename = OUTPUT_FILE_CSV_PATH + account_record.account_type.replace(" ", "_") +  "_" + account_record.account_number  + "_" + statement_year + "_" + statement_month+".csv"
        account_entries.to_csv(filename)
        return filename
    except Exception as e:
        raise Exception('Cannot transform account record to csv : ' + str(e))

def pdf_data_to_csv(pdf_data_list: list[PDFData]):
    return_file_names = []
    for pdf_data in pdf_data_list:
            for ar in pdf_data.account_records:
                filename = account_record_to_csv(ar)
                return_file_names.append(os.path.basename(filename))
    return return_file_names

def pdf_data_to_json(pdf_data_list: list[PDFData], file_path: str = ""):
    raw_records = []
    return_file_name = os.path.basename(file_path)
    try:
        for pdf_data in pdf_data_list:
            for ar in pdf_data.account_records:
                raw_records = raw_records + account_record_to_raw_records(pdf_data.file_name, ar)
    except Exception as e:
        raise Exception("Cannot create json file with error: " + str(e))

    else:
        if file_path != "":
            with open(file_path, "w") as outfile:      
                json_string = json.dumps([ob.__dict__ for ob in raw_records])
                outfile.write(json_string)  
        return return_file_name

def main():
    print ('The program is now start....... \n')
    dir_list = os.listdir(TO_BE_PROCESS_FOLDER_PATH)
    dir_list.sort()
    print("The file will be processed:")
    print(dir_list)
    print("\n")

    pdf_data_list = []
    try:
        for file in dir_list:
            if file.endswith(".pdf"):
                pdf_data_list.append(get_pdf_data(TO_BE_PROCESS_FOLDER_PATH + file))
        csv_files_name = pdf_data_to_csv(pdf_data_list)
        json_file_names = pdf_data_to_json(pdf_data_list, OUTPUT_FILE_JSON_PATH)   
        print("Output csv files: ")
        print(csv_files_name)
        print("\n")

        print("Output json files: ")
        print(json_file_names)
        print("\n")

        print ('The program is  end!')

    except Exception as e:
        print("Cannot transform err: " + str(e))
        
main()




