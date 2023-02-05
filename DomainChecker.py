""" DomainChecker using GoDaddy API for bulk availability checking of domains

DomainChecker supports multiple search types which can be configured through the associated config file: single-search
using the command line; specific-search using the 'root_domains' and 'tlds' csv files; and general search, searching
all possible, domain-valid strings under a given length. The latter two search types export their results to a
formatted Excel spreadsheet. This script was designed with the intention of being run on a regular basis, so all
options can be found in the aforementioned config such that they can be set accordingly and the script running can be
automated.

    Author:         Mattias Przyrembel
    Start Date:     September 2022
    Client:         Ben @ Cre8ive IT
"""

__author__ = "Mattias Przyrembel"
__maintainer__ = "Mattias Przyrembel"
__status__ = "Production"
__version__ = "1.3"


from requests import get, exceptions
from json import load
from time import time, sleep, strftime
from os.path import isdir
from os import mkdir
from sys import exit
from string import ascii_lowercase, digits
import csv
import pandas
import warnings
import atexit

warnings.filterwarnings(action='ignore', category=FutureWarning)


def export_to_excel(dataframe, filename):
    """ Exports a pandas dataframe to an excel spreadsheet """
    try:
        # Setup excel writer, workbook and sheet
        writer = pandas.ExcelWriter(filepath + filename + ".xlsx", engine='xlsxwriter')
        dataframe.to_excel(writer, sheet_name="Sheet1")
        workbook = writer.book
        sheet = writer.sheets["Sheet1"]
        # Get the dimensions of the dataframe and adjust column size
        (max_row, max_col) = dataframe.shape
        sheet.set_column(0, max_col, 10)
        # Add conditional formatting and freeze frames
        sheet.freeze_panes(1, 1)
        avail_form = workbook.add_format({'bg_color': '#C6EFCE', 'font_color': '#006100'})
        unavail_form = workbook.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006'})
        sheet.conditional_format(1, 1, max_row, max_col,
                                 {'type': 'cell',
                                  'criteria': 'equal to',
                                  'value': '"Available"',
                                  'format': avail_form})
        sheet.conditional_format(1, 1, max_row, max_col,
                                 {'type': 'cell',
                                  'criteria': 'equal to',
                                  'value': '"Unavailable"',
                                  'format': unavail_form})
        writer.save()  # TODO: Change to use 'with open'... and remove filter warning
    except OSError:
        log_print("ERROR:\tFile export location/path is invalid")
        log_print("STATUS:\tAborting due to above error")
        exit(1)


def get_status(string):
    """ Gets the status of the param domain string (root + tld) """
    headers = {'Accept': 'application/json', 'Content-Type': 'application/json',
               'Authorization': 'sso-key {}:{}'.format(api_key, secret_key)}
    url = "https://" + api_domain + "/v1/domains/available"
    try:
        response = get(url, params={'domain': string, 'checkType': 'FULL'}, headers=headers, timeout=10)
        json = response.json()
    except exceptions.RequestException:
        count = globals()['net_attempt_counts']
        if count == 0:
            print("\r", sep="", end="")
        if count < 5:
            sleep_len = 20*(count+1)
            log_print("ERROR:\tNetwork based error has occurred while getting status")
            log_print("INFO:\tWill reattempt in {} seconds. Attempt {}".format(sleep_len, count+1), to_print=False)
            sleep(5)
            globals()['net_attempt_counts'] += 1
            return get_status(string)
        else:
            log_print("STATUS:\t{} failed attempts have occurred. Program paused.".format(count))
            junk = input("Please check network connectivity and the press enter to continue:")
            log_print("INFO:\tUser input provided. Retrying get request.")
            return get_status(string)
    try:
        globals()['net_attempt_counts'] = 0
        if "available" in json:
            match json["available"]:
                case True:
                    return "Available"
                case False:
                    return "Unavailable"
        else:
            match json["code"]:
                case "TOO_MANY_REQUESTS":
                    log_print("INFO:\tAPI call limit exceeded. Sleeping {} seconds".format(json["retryAfterSec"]),
                              False)
                    sleep(json["retryAfterSec"])
                    globals()['cpm_t0'] = time()
                    return get_status(string)
                # case "401":  # String equivalent unknown, so has been commented out
                #     log_print("ERROR:\tAPI Authentication Error (Invalid)")
                #     log_print("INFO:\tAborting due to above error")
                #     exit(1)
                # case "403":  # String equivalent unknown, so has been commented out
                #     log_print("ERROR:\tAPI Authentication Error (No Access)")
                #     log_print("INFO:\tAborting due to above error")
                #     exit(1)
                case _:
                    log_print("ERROR:\tAPI Error for domain: \"" + string + "\"", False)
                    log_print("\t\tError Code: " + json["code"] + "\tMessage: " + json["message"], False)
                    return "Unknown"
    except KeyError:
        log_print("ERROR:\tAPI Response Error when conducting search")
        log_print("STATUS:\tAborting due to above error")
        exit(1)


def get_data(top_level_domains, root_domains):
    """ Checks the availability [calls the get_status() function] of each instance in the cartesian product of the
    root and TLD sets """
    data = {}
    globals()['cpm_t0'] = time()
    req_counter = 0
    load_counter = 0
    for top in top_level_domains:
        vals = []
        for root in root_domains:
            url = root + top
            vals.append(get_status(url))
            req_counter += 1
            if req_counter % 5 == 0:  # Display loading text to indicate script has not frozen
                load_str = "Loading "
                match (load_counter % 4):
                    case 0:
                        load_str += "\\"
                    case 1:
                        load_str += "|"
                    case 2:
                        load_str += "/"
                    case 3:
                        load_str += "\u2015"
                print("\r", load_str, sep="", end="")
                load_counter += 1
            if calls_per_min > 0 and req_counter % calls_per_min == 0:  # Ensure not to exceed API limit
                if time() - globals()['cpm_t0'] < 60:
                    sleep(60 - (time() - globals()['cpm_t0']))
                globals()['cpm_t0'] = time()
        for j in range(len(root_domains)):
            data.update({top: vals})
    log_print("\rINFO:\tSearch Complete")
    return data


def get_all_valid_tlds():
    """ Function to get all TLDs supported by the API; is largely unneeded after first run to create output """
    log_print("INFO:\tUpdating list of all valid TLDs")
    headers = {'Accept': 'application/json', 'Content-Type': 'application/json',
               'Authorization': 'sso-key {}:{}'.format(api_key, secret_key)}
    url = "https://" + api_domain + "/v1/domains/tlds"
    response = get(url, headers=headers)
    json = response.json()
    try:
        vals = []
        if isinstance(json, dict):
            raise KeyError
        for x in json:
            vals.append(x["name"])
        with open('all_tlds.csv', "w", newline='') as csv_file:
            for v in vals:
                csv_file.write(".")
                csv_file.write(v)
                csv_file.write('\n')
        log_print("INFO:\tValid TLDs list had been updated")
    except KeyError:
        log_print("ERROR:\t" + json["code"] + "\tMessage: " + json["message"])
        log_print("INFO:\tValid TLDs could not be updated")


def is_valid_domain(string):
    """ Helper function to check if a domain is valid """
    valid_chars = possible_vals + "."
    if string.find(".") != -1:
        if (not all(c in valid_chars for c in string)) or string[0] == '-' or string[string.find(".") - 1] == '-' \
                or "--" in string or ".." in string:
            return False
    else:
        if (not all(c in possible_vals for c in string)) or string[0] == '-' or string[-1] == '-' \
                or "--" in string:
            return False
    return True


def import_tlds():
    """ Imports the TLDs to be searched from the 'tlds.csv' file """
    top_level_domains = []
    with open('tlds.csv', newline='') as input_file:
        for row in csv.reader(input_file):
            top_level_domains.append(row[0])
    return top_level_domains


def import_root_domains():
    """ Imports the root domains to be searched from the 'root_domains.csv' file """
    root_domains = []
    with open('root_domains.csv', newline='') as input_file:
        for row in csv.reader(input_file):
            if is_valid_domain(row[0]):
                root_domains.append(row[0])
    return root_domains


def specific_search():
    """ Starts the specific search process; establishes object values and calls sub-functions """
    log_print("INFO:\tBeginning search using specified root domains")
    # Get root domains and top-level domains from the csvs
    top_level_domains = import_tlds()
    root_domains = import_root_domains()
    if not root_domains or not top_level_domains:
        log_print("INFO:\tRoot or TLD list is empty. No data to export")
    else:
        # Get the statuses of the domains' availabilities and convert it to a DataFrame
        data = get_data(top_level_domains, root_domains)
        df = pandas.DataFrame(data, index=root_domains)
        # Export the data
        export_to_excel(df, "DomainResults")
        log_print("INFO:\tSpecific Search Data Exported")


def create_gen_root_2():
    """ Creates a list of all possible strings that can be used as a root domain that are 2 chars in length """
    strings = []
    for i in possible_vals[possible_vals.index(gen_s_begin[0]):possible_vals.index(gen_s_end[0])+1]:
        for j in possible_vals[:-1]:
            word = i + j
            if is_valid_domain(word):
                if get_general_value(word) < gen_s_min_val:
                    pass
                elif get_general_value(word) > gen_s_max_val:
                    return strings
                else:
                    strings.append(word)
    return strings


def create_gen_root_3():
    """ Creates a list of all possible strings that can be used as a root domain that are 3 chars in length """
    strings = []
    for i in possible_vals[possible_vals.index(gen_s_begin[0]):possible_vals.index(gen_s_end[0])+1]:
        for j in possible_vals:
            for k in possible_vals[:-1]:
                word = i + j + k
                if is_valid_domain(word):
                    if get_general_value(word) < gen_s_min_val:
                        pass
                    elif get_general_value(word) > gen_s_max_val:
                        return strings
                    else:
                        strings.append(word)
    return strings


def create_gen_root_4():
    """ Creates a list of all possible strings that can be used as a root domain that are 4 chars in length """
    strings = []
    for i in possible_vals[possible_vals.index(gen_s_begin[0]):possible_vals.index(gen_s_end[0])+1]:
        for j in possible_vals:
            for k in possible_vals:
                for l in possible_vals[:-1]:
                    word = i + j + k + l
                    if is_valid_domain(word):
                        if get_general_value(word) < gen_s_min_val:
                            pass
                        elif get_general_value(word) > gen_s_max_val:
                            return strings
                        else:
                            strings.append(word)
    return strings


def create_gen_root_5_end4(fchar):
    """ Creates a list of all possible strings that can be used as a root domain that are 4 chars in length with the
    param char prepended to each [list of strings w/ len 5 char] """
    strings = []
    for i in possible_vals:
        for j in possible_vals:
            for k in possible_vals:
                for l in possible_vals[:-1]:
                    word = i + j + k + l
                    if word[-1] != '-' and "--" not in word:
                        print(fchar+word, get_general_value(fchar+word))
                        if get_general_value(fchar+word) < gen_s_min_val:
                            print("Less")
                            pass
                        elif get_general_value(fchar+word) > gen_s_max_val:
                            print("returning")
                            return strings
                        else:
                            strings.append(fchar+word)
    return strings


def general_search(length, char=""):
    """ Starts the general search process; establishes object values and calls sub-functions """
    if char == "":
        log_print("INFO:\tBeginning search with root domains of " + str(length) + " characters")
    else:
        log_print("INFO:\tBeginning search with root domains of " + str(length) + " characters, beginning with " + char)
    # Get the top-level domains from the csv and generate the root domains
    top_level_domains = import_tlds()
    root_domains = []
    match length:
        case 2:
            root_domains = create_gen_root_2()
        case 3:
            root_domains = create_gen_root_3()
        case 4:
            root_domains = create_gen_root_4()
        case 5:
            root_domains = create_gen_root_5_end4(char)
        case _:
            log_print("STATUS:\tAborting due to error with general search length")
            log_print("INFO:\tThis should be impossible, so contact me if you're reading this")
            exit(1)
    if not root_domains or not top_level_domains:
        log_print("INFO:\tRoot or TLD list is empty. No data to export")
    else:
        # Get the statuses of the domains' availabilities and convert it to a DataFrame
        data = get_data(top_level_domains, root_domains)
        df = pandas.DataFrame(data, index=root_domains)
        # Export the data
        if length < 5:
            export_to_excel(df, "DomainResults" + str(length) + "chars_" +
                            gen_s_begin + "-" + gen_s_end)
        else:
            export_to_excel(df, "5chars/DomainResults" + str(length) + "begin" + char.upper())
        log_print("INFO:\tGeneral Search Data Exported")


def get_general_value(word):
    """ Helper function used to determine the 'value' of a word; used when ranking words and defining ranges for the
    general search """
    ret = 0
    for i, v in enumerate(reversed(word)):
        ret += possible_vals.index(v) * pow(37, i)
    return ret


def set_general_bounds(len_str):
    """ Sets the upper and lower bounds used in the general search """
    globals()['gen_s_begin'] = config["gen_"+len_str+"_begin"]
    globals()['gen_s_end'] = config["gen_"+len_str+"_end"]
    globals()['gen_s_min_val'] = get_general_value(gen_s_begin)
    globals()['gen_s_max_val'] = get_general_value(gen_s_end)


def log_print(string, to_print=True):
    """ Log function for printing to the user and also saving to a log txt file """
    # TODO: Change function to use built-in Python logging
    if to_print:
        print(string)
    with open("logs/" + log_title + ".txt", "a") as log_file:
        log_file.write(strftime("%H:%M:%S\t"))
        if string[0] == "\r":
            log_file.write(string[1:])
        else:
            log_file.write(string)
        log_file.write("\n")


def check_make_folder(path):
    """ Helper function for checking the existence of a folder, and if it doesn't exist, creating it """
    if not isdir(path):
        mkdir(path)


def exit_func():
    """ Atexit function used to stop the compiled program's cmd window from closing on exit """
    junk = input("Press enter to close the program:")


if __name__ == "__main__":
    # Begin logging
    check_make_folder("logs")
    log_title = strftime("log_%Y%m%d_%H%M%S")
    with open("logs/" + log_title + ".txt", "a") as log_f:
        log_f.write("Log file for DomainChecker using the GoDaddy API. Written by Mattias for Ben @ Cre8ive IT\n")
        log_f.write(strftime("Log file for run beginning: %x %X\n\n"))
    try:
        # Check existence of config json and read data accordingly
        f = open('config.json')
        config = load(f)
        f.close()
        api_domain = config["api_domain"]
        api_key = config["api_key"]
        secret_key = config["secret_key"]
        calls_per_min = config["calls_per_min"]
        cpm_t0 = time()
        net_attempt_counts = 0
        log_print("--Launching DomainChecker--")
        possible_vals = ascii_lowercase + digits + "-"
        if config["single_search"]:
            # Start the command-line based search process for manual searches
            single_search_string = ""
            while single_search_string.lower() != "exit":
                single_search_string = input(
                    "Please enter the domain to be searched for (root and TLD) or type \"exit\": ")
                if single_search_string.lower() == "dev" and \
                        (config["run_specific_search"] and config["run_general_search"]):
                    log_print("\tProgram developed by Mattias Przyrembel for Ben @ Cre8ive IT")
                elif single_search_string.lower() != "exit":
                    if '.' not in single_search_string or not is_valid_domain(single_search_string):
                        print("Invalid entry. That is not a full and valid domain.")
                    else:
                        log_print("\"" + single_search_string + "\" is: " + get_status(single_search_string))
        else:
            # Else will conduct bulk search; will have file exports, so check export location validity
            filepath = ""
            if config["filepath"] != "./":
                if isdir(config["filepath"]):
                    filepath = config["filepath"]
                    if filepath[-1] != '\\':
                        filepath += "\\"
                        check_make_folder(filepath + "\\5chars")
                else:
                    log_print("INFO:\tInvalid filepath - will export to default location")
                    check_make_folder("outputs")
                    check_make_folder("outputs\\5chars")
            else:
                check_make_folder("outputs")
                check_make_folder("outputs\\5chars")
                filepath = "outputs/"
            atexit.register(exit_func)
            if config["get_tlds"]:  # run search to update csv of all TLDs supported by the API
                get_all_valid_tlds()
            if config["run_specific_search"]:  # run search using provided root and TLD csvs
                specific_search()
            if config["run_general_search"]:  # run search using provided TLDs for all possible roots of given length
                # define global variables for word value (used when specifying ranges in general search)
                gen_s_begin = ""
                gen_s_end = ""
                gen_s_min_val = 0
                gen_s_max_val = 0
                # run general searches based on the selected lengths and their specified ranges
                if config["general_2"]:
                    set_general_bounds("2")
                    general_search(2)
                if config["general_3"]:
                    set_general_bounds("3")
                    general_search(3)
                if config["general_4"]:
                    set_general_bounds("4")
                    general_search(4)
                if config["general_5"]:
                    # given its runtime and resulting file size, len5 has been broken up by first char
                    set_general_bounds("5")
                    for first_char in possible_vals[
                                      possible_vals.index(gen_s_begin[0]):possible_vals.index(gen_s_end[0])+1]:
                        general_search(5, first_char)
                if gen_s_end == "":
                    log_print("INFO:\tGlobal general is true, but no lengths were set true. No search data exported.")
        log_print("--Exiting DomainChecker--")
    except FileNotFoundError:
        log_print("ERROR:\tCritical file (" + FileNotFoundError.filename + ") cannot be found")
        log_print("STATUS:\tAborting due to above error")
        exit(1)
