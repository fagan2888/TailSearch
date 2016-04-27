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


def get_csv(carrier, origin, date):
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
    bts = 'https://1bts.rita.dot.gov/xml/ontimesummarystatistics/src/dstat/OntimeSummaryDepaturesDataCSV.xml'

    # Dummy data (some values required by BTS)
    mydata = {'adtime':'Actual departure time', 'aetime':'Actual elapsed time'}

    # Parse the month, day, and year from the date string
    month = int(date[0:2])
    day = int(date[2:4])
    year = int(date[4:8])

    # Add appropriate form data from passed-in parameters
    # The dict keys are determined based on BTS form data
    mydata['month'+str(month)]=month
    mydata['Day'+str(day)]=day
    mydata['year'+str(year-1994)]=year
    mydata['airport1']=origin
    mydata['airline']=carrier

    # Strip off useless BTS headers from csv
    rawcsv = requests.post(bts,data=mydata).text
    t1 = rawcsv.split('\n')
    mycsv = '\n'.join(t1[15:len(t1)-2]).replace('  ','')

    # Strip off the last empty line
    result = mycsv[0:len(mycsv)-1]

    return result


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

    # Format the flight number to have leading zeroes
    fn = str(number).zfill(4)

    # Check for faulty flight numbers
    if fn not in df['Flight Number'].values:
        return 'Invalid Flight Number'

    # For the row with the specified flight number, return its tail number
    nose = df[df['Flight Number']==fn]['Tail Number'].iloc[0]

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
    rz = {'registry':'',
          'searchMsn':'',
          'searchTyp':'',
          'searchSelcal':'',
          'fleet':fleet,
          'opid1':'',
          'company1':'',
          'built':'',
          'searchNte':'',
          'frstatus':'any',
          'submitB':'search'}

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
    rzjet = requests.post('http://rzjets.net/aircraft/index.php',data=rz,headers=h)

    # Scrape the RJZets response
    tail = BeautifulSoup(rzjet.text, 'lxml')

    # The third <tr> tag will be the first aircraft entry
    tr = tail.find_all('tr')[3]

    # The first <a> tag will contain the tail number
    a = tr.find('a')

    return a.text


def get_tail(flight,origin,date):
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
    number = flight[2:len(flight)]

    # Get our CSV, then DataFrame, then the nose number
    csv = get_csv(carrier,origin,date)
    df = get_df_from_csv(csv)
    nose = get_nose(df,number)

    # If the BTS result follows the AA nose number scheme, we will call get_fleet
    # The nose number scheme is N followed by a number, two letters, and then finally AA
    if re.match('N\d[A-Z]{2}A{2}', nose):
        print('This is a nose number!')
        fleet = nose[1:4]
        print('Fleet: '+fleet)
        return get_fleet(fleet)

    # Otherwise we simply return the number we found above
    else:
        return nose