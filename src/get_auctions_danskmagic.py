'''
download and evaluate upcoming auctions on danskmagic.com
outputs a summary table to ./output/auctions/danskmagic/

# TODO: when evaluating against cutoff by when the auction was posted, first check 'seneste'. If any of those are too old, no need to check the rest.

# usage:
## check auctions put online within the last day
poetry run python ./src/get_auctions_danskmagic.py -u _JonT_ -p bonzaibennygonzalez -s "alpha,beta,unlimited,revised,legends,arabian nights,antiquities,the dark,ice age,alliances,homelands,fallen empires,4th edition,5th edition,mirage,weatherlight,visions,tempest,stronghold,exodus" -f ./output/pricehistory/1990s_all_pricehist_20210915_123307.csv -b "2019-12-31" -e "2021-12-31"  -l 15 -m 10000 -r 1.15 -t 30 -o 99
## check auctions closing in the next day
poetry run python ./src/get_auctions_danskmagic.py -u _JonT_ -p bonzaibennygonzalez -s "alpha,beta,unlimited,revised,legends,arabian nights,antiquities,the dark,ice age,alliances,homelands,fallen empires,4th edition,5th edition,mirage,weatherlight,visions,tempest,stronghold,exodus" -f ./output/pricehistory/1990s_all_pricehist_20210915_123307.csv -b "2019-12-31" -e "2021-12-31"  -l 15 -m 10000 -r 1 -t 1 -o 999 --value_median_lowest 0.5
'''

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
# from selenium.webdriver.support import expected_conditions as EC
import time, os
import pandas as pd 
import argparse
import re
from datetime import datetime, timedelta
from numpy import nan

# Initialize parser
parser = argparse.ArgumentParser(description='Download danskmagic auction as table')

# Add parser arguments
parser.add_argument("-u", "--username", dest="username", type=str, help = "www.danskmagic.com account username")
parser.add_argument("-p", "--password", dest="password", type=str, help = "www.danskmagic.com account password")
parser.add_argument("-c", "--chromedriverpath", dest="chromedriverpath",  type=str,  help = "Path to chromedriver executable (default: /Applications/chromedriver)", default="/Applications/chromedriver")
parser.add_argument("-s","--sets",dest="sets",type=str, help = "a string of sets to accept e.g. 'alpha,beta,unlimited,revised'. Case insensitive.)", default=None)
#parser.add_argument("auctionids",type=str, nargs="+", help = "www.danskmagic.com auction ids, accepts many arguments")
parser.add_argument("-o", "--time_online_days_max", dest="time_online_days_max", type=int, help = "Max days auction has been up", default=2)
parser.add_argument("-t", "--time_left_days_max", dest="time_left_days_max", type=int, help = "Max days left in auction", default=99)
parser.add_argument("-f","--pricehistoryfile",dest="pricehistoryfile",type=str, help = "pricehistory csv file as produced by get_prices.py")
parser.add_argument("-b", "--pricehistory_interval_begin", dest="pricehistory_interval_begin", type=str, help = "end date for time interval to use for calculating price history statistics", default="2020-01-01")
parser.add_argument("-e", "--pricehistory_interval_end", dest="pricehistory_interval_end", type=str, help = "end date for time interval to use for calculating price history statistics", default="2022-01-01")
parser.add_argument("-l", "--value_median_lowest", dest="value_median_lowest", type=float, help = "minimum median card price in dollars to consider", default=15)
parser.add_argument("-m", "--value_median_max", dest="value_median_max", type=float, help = "maximum median card value to consider", default=2500)
parser.add_argument("-r", "--bid_median_value_ratio_threshold", dest="bid_median_value_ratio_threshold", type=float, help = "threshold auction price/median price value to consider for a bid", default=1.25)

# interactive testing
if False:
    username = "_JonT_"
    password = "bonzaibennygonzalez"
    chromedriverpath = "/Applications/chromedriver"
    sets = "alpha,beta,unlimited,revised,legends,arabian nights,antiquities,the dark,alliances,homelands,fallen empires,4th edition,5th edition,mirage,weatherlight,visions,tempest,stronghold,exodus,urza's destiny,urza's legacy,urza's saga"
    time_online_days_max = 2
    time_left_days_max = 99 
    pricehistoryfile = "./output/pricehistory/1990s_all_pricehist_20210619_220609.csv"
    value_median_lowest = 20
    value_median_max = 2500
    bid_median_value_ratio_threshold = 1.25
    pricehistory_interval_begin = "2020-01-01"
    pricehistory_interval_end = "2021-12-31"


# Read arguments from command line
args = parser.parse_args()

rootdir = re.sub(re.compile("/src|/data/*|/output/*|/config"),"",os.getcwd())
today_str = datetime.today().strftime('%Y-%m-%d_%H.%M.%S')
until = datetime.today() + timedelta(days=args.time_left_days_max)
until_str = until.strftime('%Y-%m-%d_%H.%M.%S')
file_out = f"{rootdir}/output/auctions/danskmagic/{today_str}__{until_str}_auctions.csv"

# LOAD HELPER TABLES
# currency conversion
df_currency_conversion = pd.read_csv(f"{rootdir}/config/currency_conversion.csv")
# card grade price factors
df_grade = pd.read_csv("./config/grade.csv")
# load price history generated with get_prices.py
df_pricehistory = pd.read_csv(args.pricehistoryfile, sep=",")
# dict set to set code used in price history
dict_set_code ={
    "Alpha":"LEA",
    "Beta":"LEB",
    "Unlimited":"2ED",
    "Revised":"3ED",
    "Legends":"LEG",
    "Arabian Nights":"ARN",
    "Antiquities":"ATQ",
    "The Dark":"DRK",
    "Fallen Empires":"FEM",
    "Ice Age":"ICE",
    "Alliances":"ALL",
    "Homelands":"HML",
    "4th Edition":"4ED",
    "5th Edition":"5ED",
    "Mirage":"MI",
    "Weatherlight":"WL",
    "Visions":"VI",
    "Tempest":"TE",
    "Stronghold":"ST",
    "Exodus":"EX",
    "Urza's Destiny":"UD",
    "Urza's Legacy":"UL",
    "Urza's Saga":"UZ"
}
dict_month = {"Jan":"01", "Feb":"02", "Mar":"03", "Apr":"04", "May":"05", "Jun":"06", "Jul":"07", "Aug":"08", "Sep":"09", "Oct":"10", "Nov":"11", "Dec":"12"}
df_pricehistory["datetime"] = pd.to_datetime(df_pricehistory["date"])

# filter price history
df_pricehistory = df_pricehistory[df_pricehistory["datetime"]<=pd.to_datetime(args.pricehistory_interval_end)] 
df_pricehistory = df_pricehistory[df_pricehistory["datetime"]>=pd.to_datetime(args.pricehistory_interval_begin)]

# start chrome driver
chrome_options = webdriver.ChromeOptions()
#chrome_options.add_experimental_option("prefs", {"download.default_directory":"~"})
chromedriver = args.chromedriverpath # path to the chromedriver executable
os.environ["webdriver.chrome.driver"] = chromedriver
driver = webdriver.Chrome(executable_path=chromedriver)#, options=chrome_options)

# navigate to page and login
driver.get("https://www.danskmagic.com/torget/index.php?what=auktion")
inputbox_username = driver.find_element_by_name("loginusername")
inputbox_password = driver.find_element_by_name("password")
button_submit = driver.find_element_by_xpath("//div[@id='loginbox']/form[1]/p[1]/input[4]")
# fill in email and password
inputbox_username.send_keys(args.username)
inputbox_password.send_keys(args.password)
button_submit.click()

time.sleep(1) # TODO: replace with proper method

# get latest auction id from 'seneste auktioner' table
#auctionid_latest =  driver.find_element_by_xpath("//td[@id='content']/table[2]/tbody[1]/tr[1]/td[1]/table[1]/tbody[1]/tr[1]/td[3]").find_element_by_class_name("box.bla").find_element_by_xpath(".//div[1]/a[1]").get_property("href").replace("https://www.danskmagic.com/torget/index.php?what=auktionen&ID=","").replace("&link=vb_al","")

# get auctionids from main table

auctionids = []

auction_table = driver.find_element_by_xpath("//td[@id='content']/table[2]/tbody[1]/tr[1]/td[1]/table[1]/tbody[1]/tr[1]/td[1]")
auction_rows = auction_table.find_elements_by_class_name("auktion-table")

for auction_row in auction_rows:    
    timeleft_str = auction_row.find_element_by_xpath(".//tbody[1]/tr[1]/td[2]").get_property("textContent")
    if not "dage" in timeleft_str or (args.time_left_days_max>= 2 and int(timeleft_str.split(" ")[0].replace("h",""))<=args.time_left_days_max):
        try:
            auctionid = auction_row.find_element_by_xpath(".//tbody[1]/tr[1]/td[1]/a[1]").get_property("href").replace("https://www.danskmagic.com/torget/index.php?what=auktionen&ID=","")
        except NoSuchElementException as e:
            #print(str(e))
            auctionid = auction_row.find_element_by_xpath(".//tbody[1]/tr[1]/td[1]/b[1]/a[1]").get_property("href").replace("https://www.danskmagic.com/torget/index.php?what=auktionen&ID=","").replace("&link=vb_al","")        
        auctionids.append(auctionid)
    else:
        break # auctions are displayed in order of deadline, so no need to check the ones below

list_df_auction = []

# if the threshold on time since auction start is smaller than threshold for time until auction finish
# go through auctions in order of recency
if args.time_online_days_max < args.time_left_days_max:
    auctionids = [int(auctionid) for auctionid in auctionids]
    auctionids.sort(reverse = True)

for auctionid in auctionids:
    list_rows = []
    conversion_factor = None
    # navigate to page and log in
    driver.get(f"https://www.danskmagic.com/torget/index.php?what=auktionen&ID={auctionid}")
  
    time.sleep(0.5) # TODO: replace with proper method

    # get auction table
    auction_head = driver.find_element_by_xpath("//td[@id='content']/table[2]/tbody[1]/tr[1]/td[1]/table[1]/tbody[1]/tr[1]/td[1]/table[1]/tbody[1]/tr[2]/td[2]").get_property("textContent")
    auction_head = re.sub(r"\n", "", auction_head)
    auction_head = re.sub(r"\t", "", auction_head)
    
    auction_starts = auction_head.split("Startede: ")[1].split(" /slutter")[0].strip()
    auction_starts = auction_starts[0:2] + "-" + dict_month[auction_starts[3:6]] + "-20" + auction_starts[8:] + ":00"
    auction_starts = auction_starts.replace(", ", " ")
    auction_starts_datetime = datetime.strptime(auction_starts, '%d-%m-%Y %H:%M:%S')
    if auction_starts_datetime < datetime.today() - timedelta(days=args.time_online_days_max):
        if args.time_online_days_max < args.time_left_days_max:# and auctionid in auctionids_latest:
            break
        else:
            continue
    
    print(f"getting auction {auctionid}")

    auction_ends = auction_head.split("/slutter: ")[1]    
    auction_ends = auction_ends[0:2] + "-" + dict_month[auction_ends[3:6]] + "-20" + auction_ends[8:] + ":00"
    auction_ends = auction_ends.replace(", ", " ")
    auction_ends_datetime = datetime.strptime(auction_ends, '%d-%m-%Y %H:%M:%S')
    #auction_ends_datetime_str = auction_ends_datetime.strftime("%Y%m%d_%H%M%S")
    
    # check for multiple pages
    parent_element = driver.find_element_by_xpath("//td[@id='content']/table[2]/tbody[1]/tr[1]/td[1]/table[1]/tbody[1]/tr[1]/td[1]")
    multipage_elements = parent_element.find_elements_by_class_name("fieldset_brun")
    if multipage_elements:
        select_element = multipage_elements[0].find_element_by_tag_name("select")
        pages = [option.get_property("value") for option in select_element.find_elements_by_tag_name("option")]
        URLs = [f"https://www.danskmagic.com/torget/index.php?what=auktionen&ID={auctionid}&action=sok&ordning=expansion&p={page}" for page in pages]
    else:
        URLs = [f"https://www.danskmagic.com/torget/index.php?what=auktionen&ID={auctionid}"]
    for k in range(len(URLs)):
        URL = URLs[k]
        print(f"page {k+1}/{len(URLs)}")
        driver.get(URL)
        time.sleep(0.5) # TODO: replace with proper method. This will fail on a slow connection.
        
        form_table = driver.find_element_by_xpath("//form[@id='bjud']/table[1]/tbody[1]")

        # check if the page includes any relevant sets; if not, skip page
        if args.sets:
            auction_sets = [set_row.get_property("textContent") for set_row in form_table.find_elements_by_class_name("bak_gra")]
            if not any([auction_set.lower() in args.sets.lower() for auction_set in auction_sets]):
                continue
        
        # iterate over table rows
        form_rows = form_table.find_elements_by_tag_name("tr")
        for form_row in form_rows:
            if form_row.get_attribute("class") == "bak_gra":
                magic_set = form_row.find_element_by_tag_name("b").get_property("textContent")
            elif form_row.get_attribute("class") in ["tr_gul1 brodtext","tr_gul2 brodtext"]: 
                # check various conditions
                if args.sets and not magic_set.lower() in args.sets.lower():
                    continue
                # card column
                column1 = form_row.find_element_by_xpath(".//td[1]")
                column1_textContent = column1.get_property("textContent")
                # check whether a flag row e.g. auktion oldschool https://www.danskmagic.com/torget/index.php?what=auktionen&ID=35697
                if column1.get_property("textContent") in [' Auktion oldschoo', ' Auktion']:
                    continue
                # check if it is a row with a user uploaded photo 
                if len(form_row.find_elements_by_tag_name("td")) == 1:
                    continue

                grade = form_row.find_elements_by_tag_name("a")[2].get_property("textContent")
                # skip cards graded 'poor' (PR)
                if grade == "PR":
                    continue
                language = "eng" if "(eng" in column1_textContent or "("+grade+")" in column1_textContent else "foreign"
                # skip non-eng cards
                if language != "eng":
                    continue 
                buyouted = True if form_row.find_elements_by_xpath(".//td[5]/b[1]") else False
                if buyouted:
                    continue 
                # try:
                #cardname = column1.find_element_by_xpath(".//a[2]").get_property("textContent")
                cardname = column1.find_element_by_class_name("popup").get_property("textContent")
                # except Exception as e:
                #     cardname = column1_textContent.split(" (")[0]
                #     print(column1_textContent)
                #     print(str(e))    
                #     cardname = column1_textContent.split(" (")[0]
                #     print(f"recovered cardname : {cardname}")
                #     #continue
                
                list_rarity = [rarity[1:-1] for rarity in ["(C)","(U)","(R)","(MR)"] if rarity in column1_textContent]
                rarity = list_rarity[0] if list_rarity else None 

                # bid column
                current_bid = form_row.find_element_by_xpath(".//td[2]/a[1]").get_property("textContent")
                current_bid_amount, current_bid_currency = current_bid.split(" ")
                current_bid_amount = float(current_bid_amount)
                # convert to USD
                if conversion_factor == None:
                    list_idx_row_1 = [i for i, x in enumerate(df_currency_conversion["currency"]==current_bid_currency) if x]
                    idx_row_1 = list_idx_row_1[0] if list_idx_row_1 else None 
                    USD_multiplier = df_currency_conversion.at[idx_row_1,"USD_multiplier"] if idx_row_1 != None else nan                        
                current_bid_USD = current_bid_amount * USD_multiplier
                
                highestbidder = form_row.find_elements_by_xpath(".//td[3]/a[1]")
                if highestbidder:
                    highestbidder_username = highestbidder[0].get_property("textContent")
                    highestbidder_userid = highestbidder[0].get_property("href")
                else: 
                    highestbidder_username = None 
                    highestbidder_userid = None 
                
                # buyout
                buyout_text = form_row.find_elements_by_xpath(".//td[4]")[0].get_property("textContent")
                if buyout_text.strip():
                    buyout_amount = float(re.sub(re.compile("\D"), "",buyout_text))
                    buyout_currency = [currency for currency in ["SEK","DKK"] if currency in buyout_text][0]
                    buyout = f"{buyout_amount} {buyout_currency}"
                else:
                    buyout_amount = nan
                    buyout_currency = None
                    buyout = None
                buyout_amount_USD = buyout_amount * USD_multiplier

                bid_box_name =  form_row.find_elements_by_xpath(".//td[5]/input[1]")[0].get_attribute("name")

                # calculate price history statistics
                cardname_match = cardname.split(" v.")[0].strip() if " v. " in cardname else cardname
                pricehistory_columnname_matches = [columnname for columnname in df_pricehistory.columns if cardname_match + "_" + dict_set_code[magic_set] in columnname] 
                if pricehistory_columnname_matches:
                    columnname = pricehistory_columnname_matches[0]

                    list_idx_row_1 = [k for k, x in enumerate(df_grade["abbreviation"] == grade.lower()) if x]
                    if list_idx_row_1:
                        price_multiplier = df_grade.at[list_idx_row_1[0],"price_multiplier"] 
                    else:
                        price_multiplier = 0.75 # apply default conservative multiplier
                        print(f"Warning: no grade for {cardname}_{magic_set}, discounting value estimates by {price_multiplier} as default. Check manually.")
                    value_median = df_pricehistory[columnname].median() * price_multiplier
                    value_mean = df_pricehistory[columnname].mean() * price_multiplier
                    value_min = df_pricehistory[columnname].min() * price_multiplier
                    value_max = df_pricehistory[columnname].max() * price_multiplier
                    
                else: 
                    print(f"Warning: {cardname}_{magic_set} produced no matches in pricehistory file")
                    value_median = value_mean = value_min = value_max = nan

                if value_median < args.value_median_lowest or value_median > args.value_median_max:
                    continue
                
                bid_median_value_ratio = current_bid_USD / value_median
                if bid_median_value_ratio > args.bid_median_value_ratio_threshold:
                    continue
                
                buyout_median_value_ratio = buyout_amount_USD / value_median 

                recommend = "yes" if bid_median_value_ratio < 0.75 else "maybe" if bid_median_value_ratio >= 0.75 and bid_median_value_ratio < 1.25 else "no"

                # put everything in array and add to dict
                list_rows.append([
                    auction_ends_datetime,
                    magic_set,
                    cardname,
                    rarity, 
                    language,
                    grade,
                    current_bid,
                    round(current_bid_USD,2),
                    highestbidder_username,
                    buyout,
                    buyout_amount_USD,
                    round(value_min,2),
                    round(value_max,2),
                    round(value_mean,2),
                    round(value_median,2),
                    round(bid_median_value_ratio,2),
                    round(buyout_median_value_ratio,2),
                    recommend,
                    round(value_median/USD_multiplier,2),
                    False,
                    auctionid,
                    bid_box_name,
                    URL,
                    None,
                    nan,
                    ])
   
    if list_rows:
        df_auction = pd.DataFrame(
            list_rows, 
            columns = [
                    "ends",
                    "magic_set",
                    "cardname",
                    "rarity", 
                    "language",
                    "grade",
                    "current_bid",
                    "current_bid_USD",
                    "highestbidder_username",
                    "buyout_price",
                    "buyout_price_USD",
                    "value_min",
                    "value_max",
                    "value_mean",
                    "value_median",
                    "bid_median_value_ratio", 
                    "buyout_median_value_ratio", 
                    "recommend",
                    f"my_bid_max_{current_bid_currency}",
                    "do_bid",
                    "auction_id",
                    "bid_box_name",
                    "URL",
                    "status",
                    "paid"
                ])
    
        list_df_auction.append(df_auction)

driver.close()

# append all the dataframes
if list_df_auction:
    df_auction = list_df_auction[0] 
    if len(list_df_auction)>1:
        df_auction = df_auction.append(other=list_df_auction[1:])

    df_auction.sort_values(by="bid_median_value_ratio", axis=0,inplace=True)
    df_auction.to_csv(path_or_buf = file_out, sep=",", header=True, index=False)    
else:
    print("No matching items")