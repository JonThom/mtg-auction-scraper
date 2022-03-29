'''
download price history for a set of MTG cards from mtggoldfish.com

# usage:
poetry run python ./src/get_prices.py -e jjt3f2188@gmail.com -p gamblinghorsetuna -i ./data/lists_fullsets/1990s_all.tsv -s "\t" -c /Applications/chromedriver 
'''

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
import time
from random import uniform 
import pandas as pd 
import argparse
from datetime import datetime
import re 
import os
from numpy import nan 

# Initialize parser
parser = argparse.ArgumentParser(description='Download MTGgoldfish price history for a list of cards')

# Add parser arguments
parser.add_argument("-e", "--email", dest="email", type=str, help = "www.mtggoldfish.com account email")
parser.add_argument("-p", "--password", dest="password", type=str, help = "www.mtggoldfish.com account password")
parser.add_argument("-i", "--inputfile", dest="inputfile", type=str, help = "full path to file with columns containing name and set (set code, see https://www.mtggoldfish.com/sets).")
parser.add_argument("-s", "--sep", dest="sep", type=str, help = "file column separator for inputfile (default ,)", default=",")
parser.add_argument("-c", "--chromedriverpath", dest="chromedriverpath",  type=str,  help = "Path to chromedriver executable (default: /Applications/chromedriver)", default="/Applications/chromedriver")
parser.add_argument("-f","--forcenewdownload",dest="forcenewdownload",type=bool, help = "if output file already exists, force new download? (default False)", default=False)
parser.add_argument("-d", "--dir_downloads", dest="dir_downloads", type=str, help = "chrome download dir", default='/Users/rkm916/Downloads/')

if False:
    email = "jjt3f2188@gmail.com "
    password = "gamblinghorsetuna" 
    inputfile = "./data/lists_fullsets/fallenempires.tsv"
    sep = "\t" 
    chromedriverpath = "/Applications/chromedriver"
    forcenewdownload = False
    dir_downloads = '/Users/rkm916/Downloads/'

# Read arguments from command line
args = parser.parse_args()

rootdir = re.sub(re.compile("/src|/data/*|/output/*|/config"),"",os.getcwd())
today = datetime.today().strftime('%Y%m%d_%H%M%S')
inputfile_truncated = re.sub(re.compile('.*/'),'',args.inputfile)
inputfile_truncated = re.sub(re.compile(r'\.txt$|\.csv$|\.tsv$'),'',inputfile_truncated)
file_out = f"{rootdir}/output/pricehistory/{inputfile_truncated}_pricehist_{today}.csv"

if not os.path.exists(file_out) or args.forcenewdownload: 

    #list_downloads = os.listdir(dir_downloads)

    # load input file with magic card names and sets
    df = pd.read_csv(args.inputfile, sep = args.sep)
    df.sort_values(by=[df.columns[1],df.columns[0]], inplace=True)
    df.index = range(df.shape[0])
    # start chrome driver
    chrome_options = webdriver.ChromeOptions()
    #chrome_options.add_experimental_option("prefs", {"download.default_directory":"~"})
    chromedriver = args.chromedriverpath # path to the chromedriver executable
    os.environ["webdriver.chrome.driver"] = chromedriver
    driver = webdriver.Chrome(executable_path=chromedriver)#, options=chrome_options)

    # navigate to page and log in
    driver.get("https://www.mtggoldfish.com/login")
    time.sleep(3) # wait for page to load fully including cookie popup
    inputbox_email = driver.find_elements_by_id("email-email")[0]
    inputbox_password = driver.find_elements_by_id("email-password")[0]
    button_submit = driver.find_elements_by_class_name("btn-primary")[0]
    # accept cookies to get rid of cookie banner
    button_cookies_accept = driver.find_elements_by_class_name("css-1litn2c")[0]
    button_cookies_accept.click()
    # fill in email and password
    inputbox_email.send_keys(args.email)
    inputbox_password.send_keys(args.password)
    button_submit.click()

    # get prices as separate csv files
    dict_df_tmp = {}

    # download files
    for idx in df.index:        
        cardname = df[df.columns[0]][idx].replace(":","_").strip()
        card_version = df[df.columns[2]][idx]
        if not card_version is nan and not card_version == None:
            card_version = str(card_version)
            if re.match(re.compile("[A-Za-z]"),card_version):
                card_version_filename = " _" + card_version + "_" 
                card_version_url = r"+%253C" + card_version + r"%253E" 
            else:
                card_version_filename = ""
                card_version_url = ""
        else:
            card_version_filename = ""
            card_version_url = ""
        
        #card_version_url = r"+%253C" + card_version + r"%253E" if not card_version is nan and not card_version == "" else ""
        card_set =  str(df[df.columns[1]][idx]).strip() 
        path_file_tmp =  args.dir_downloads + cardname + card_version_filename + " [" + card_set + "].csv"
        if not os.path.exists(path_file_tmp) or args.forcenewdownload: # only download if absent or force   
            time.sleep(uniform(0.5,0.75)) # avoid getting throttled
            try:
                price_url = r"https://www.mtggoldfish.com/price-download/paper/" + cardname.replace(' ','+') + card_version_url + r"+%255B" + card_set + r"%255D"
                driver.get(price_url)
            except Exception:
                try:
                    price_url = r"https://www.mtggoldfish.com/price-download/paper/" + cardname.replace(' ','+') + card_version_url + r"+%5B" + card_set + r"%5D"
                    print("price_url alternate")
                    print(price_url)
                    driver.get(price_url)
                except Exception as e:
                    print(path_file_tmp + " failed with error " + str(e))
    time.sleep(1.5) # wait for last file to download
    
    driver.close()

    # collate files
    for idx in df.index:
        cardname = df[df.columns[0]][idx].replace(":","_").strip()
        card_set =  str(df[df.columns[1]][idx]).strip() 
        card_version = df[df.columns[2]][idx]
        if not card_version is nan and not card_version == None:
            card_version = str(card_version)
            if re.match(re.compile("[A-Za-z]"),card_version):
                card_version_filename = " _" + card_version + "_" 
            else:
                card_version_filename = ""
        else:
            card_version_filename = ""
        #card_version_url = r"+%253C" + card_version + r"%253E" if not card_version is nan and not card_version == "" else ""
        card_set_filename = "[" + str(df[df.columns[1]][idx]).strip() + "]"
        path_file_tmp =  args.dir_downloads + cardname + card_version_filename + " " + card_set_filename + ".csv"
        columnname = cardname + "_" + card_set 
        if card_version_filename:
            columnname += "_" + card_version
        if os.path.exists(path_file_tmp):
            # make sure file isn't empty
            if os.path.getsize(path_file_tmp):
                #print(df[df.columns[0]][idx].strip()  + ": file not empty")
                df_tmp = pd.read_csv(path_file_tmp, index_col=0, sep=",", header=None)
                df_tmp.columns = ["value"]
                dict_df_tmp[columnname] = df_tmp
            else:
                print(path_file_tmp  + ": empty file, check file URL")
                os.remove(path_file_tmp)
        else: 
            print(path_file_tmp  + ": file does not exist, check file URL")
            
    # collect all in one df 
    df_pricehistory = pd.concat(dict_df_tmp, axis=1, ignore_index= True, join="outer")
    df_pricehistory.columns = dict_df_tmp.keys()
    df_pricehistory = df_pricehistory.rename_axis("date")
    # df_pricehistory["date"] = list(df_pricehistory.index)
    df_pricehistory.to_csv(path_or_buf = file_out, sep=",", header=True)
else:
    print(f"{file_out} already exists - use -f True to overwrite")