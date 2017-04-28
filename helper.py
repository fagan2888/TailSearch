#!/usr/bin/env python

"""helper.py: A helper function that will allow the easy retrieval of tail numbers from flight information"""

import requests
import pandas as pd
from bs4 import BeautifulSoup
import lxml
import re


__author__ = "Akhil Tandon"
__copyright__ = "(c) 2016"

__license__ = "GPL"
__version__ = "1.0"


def get_bts(carrier, origin, date):
    """
    Posts a request to BTS by parsing carrier, origin, and date and retrieves a CSV

    Parameters
    ----------
    carrier: a string
    origin: a string
    date: a string

    Returns
    -------
    A CSV (as a string)
    """

    # BTS website to collect CSV

    bts = 'https://www.transtats.bts.gov/ONTIME/Departures.aspx'

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116 Safari/537.36"
    }

    # Create requests session
    s = requests.Session()
    r = s.get(bts, headers=headers)

    soup = BeautifulSoup(r.content, 'lxml')

    viewState = soup.select_one('#__VIEWSTATE')["value"]
    viewStateGenerator = soup.select_one('#__VIEWSTATEGENERATOR')["value"]
    eventValidation = soup.select_one('#__EVENTVALIDATION')["value"]

    # Dummy data (some values required by BTS)
    mydata = {'__EVENTTARGET': 'DL_CSV', '__EVENTARGUMENT': '', '__VIEWSTATE': viewState,
              '__VIEWSTATEGENERATOR': viewStateGenerator,'__EVENTVALIDATION': eventValidation,
              'chkStatistics$1': 1, 'chkStatistics$3': 3}

    # Parse the month, day, and year from the date string
    month = int(date[0:2])
    day = int(date[2:4])
    year = int(date[4:8])

    # Add appropriate form data from passed-in parameters
    # The dict keys are determined based on BTS form data
    mydata['chkMonths$' + str(month - 1)] = month
    mydata['chkDays$' + str(day - 1)] = day
    mydata['chkYears$' + str(year - 1987)] = year
    mydata['cboAirport'] = origin
    mydata['cboAirline'] = carrier
    mydata['btnSubmit'] = 'Submit'

    rawdata = s.post(bts, data=mydata, headers=headers).text
    result = BeautifulSoup(rawdata, 'lxml')
    table = result.find('table',{'id':'GridView1'})
    df = pd.read_html(str(table),header=0)

    return df[0]


def get_df_from_csv(csv):
    """
    Converts raw CSV data into a Pandas DataFrame (without using the CSV module)

    Parameters
    ----------
    csv: a string in CSV format

    Returns
    -------
    A pandas.DataFrame
    """

    # First split to create rows
    s1 = csv.split(',\n')

    # For each row, split to create individual values
    s2 = list()
    for i in s1:
        s2.append(i.split(','))

    # Create a Data frame, using the first row as column names
    df = pd.DataFrame(s2[1:len(s2)], columns=s2[0])

    return df


def get_nose(df, number):
    """
    Get the tail (or nose for American Airlines) number from the data frame

    Parameters
    ----------
    df: a pandas.DataFrame
    number: an int (or string) containing the flight number

    Returns
    -------
    A string
    """

    # Check for faulty flight numbers
    if number not in df['Flight Number'].values:
        return 'Invalid Flight Number'

    # For the row with the specified flight number, return its tail number
    nose = df[df['Flight Number'] == number]['Tail Number'].iloc[0]

    return nose


def get_fleet(fleet):
    """
    Function only called for American Airlines (which reports nose numbers to BTS rather than tail numbers)

    Parameters
    ----------
    fleet: a string containing the fleet number

    Returns
    -------
    A string containing the tail number
    """

    # Required data for the RZJets database with the value of fleet set
    rz = {'registry': '',
          'searchMsn': '',
          'searchTyp': '',
          'searchSelcal': '',
          'fleet': fleet,
          'opid1': '',
          'company1': '',
          'built': '',
          'searchNte': '',
          'frstatus': 'any',
          'submitB': 'search'}

    # Required headers for RZJets
    h = {'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
         'Accept-Encoding': 'gzip, deflate',
         'Accept-Language': 'en-US,en;q=0.8',
         'Cache-Control': 'max-age=0',
         'Connection': 'keep-alive',
         'Content-Length': '118',
         'Content-Type': 'application/x-www-form-urlencoded',
         'Cookie': 'PHPSESSID=9d6dab3e982a7798a4a986d7c8ece062',
         'Host': 'rzjets.net',
         'Origin': 'http://rzjets.net',
         'Referer': 'http://rzjets.net/aircraft/index.php',
         'Upgrade-Insecure-Requests': '1',
         'User-Agent': 'Mozilla/5.0'}

    # Post a request to the RZJets database
    rzjet = requests.post('http://rzjets.net/aircraft/index.php', data=rz, headers=h)

    # Scrape the RJZets response
    tail = BeautifulSoup(rzjet.text, 'lxml')

    # The third <tr> tag will be the first aircraft entry
    tr = tail.find_all('tr')[3]

    # The first <a> tag will contain the tail number
    a = tr.find('a')

    return a.text.encode('utf-8')


def get_tail(flight, origin, date):
    """
    Our main function which calls our helper functions to product the tail number

    Parameters
    ----------
    flight: a string containing the fleet number
    origin: a string containing the origin airport
    date: a string containing the date in MMDDYYYY

    Returns
    -------
    A string containing the tail number
    """

    # Parse carrier and flight number information
    carrier = flight[0:2]
    number = int(flight[2:len(flight)])

    # Get our CSV, then DataFrame, then the nose number
    df = get_bts(carrier, origin, date)
    nose = get_nose(df, number)

    # If the BTS result follows the AA nose number scheme, we will call get_fleet
    # The nose number scheme is N followed by a number, two letters, and then finally AA
    if re.match('N\d[A-Z]{2}A{2}', nose):
        print('This is a nose number!')
        fleet = nose[1:4]
        print('Fleet: ' + fleet)
        return get_fleet(fleet)

    # Otherwise we simply return the number we found above
    else:
        return nose
