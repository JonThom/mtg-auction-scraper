'''
sum price histories for sets of MTG cards from mtggoldfish.com 

# usage:
poetry run python ../src/plot_prices_sum.py -o 20210617_price_history_sum  -r 1500 price_history_3ED_all.csv price_history_4ED_all.csv  price_history_ALL_all.csv price_history_ICE_all.csv price_history_HML_all.csv price_history_FEM_all.csv price_history_MIR_all.csv price_history_VIS_all.csv  price_history_STH_all.csv  price_history_WTH_all.csv price_history_CHR_all.csv price_history_EXO_all.csv price_history_TMP_all.csv
'''

import pandas as pd 
import numpy as np
import argparse
import altair as alt
import os 
import datetime 
import re 

# Initialize parser
parser = argparse.ArgumentParser(description='Download MTGgoldfish price history for a list of cards')

# Add parser arguments
parser.add_argument("-l", "--log10", dest="log10", type=bool, help = "plot y-axis on log10 scale. Useful for being able to make out lower prices when there are extremely high prices, (default False)", default=False)
parser.add_argument("-w", "--width", dest="width", type=int, help = "plot width in px (default 2000)", default="2000")
parser.add_argument("-f", "--fillmissingvalues", dest="fillmissingvalues", type=bool, help = "Carry forward last known value to fill missing values? (default True)", default=True)
parser.add_argument("-c", "--clip", dest="clip", type=int, help = "threshold at which to clip values (sets them to max)? int, (default 5000)", default=5000)
parser.add_argument("-r", "--remove", dest="remove", type=int, help = "threshold at which to remove values (sets them to max)? int, (default 10000)", default=10000)
parser.add_argument("pricehistoryfiles",type=str, nargs="+", help = "pricehistory csv files as returned by get_prices.py")

# Read arguments from command line
args = parser.parse_args()

rootdir = re.sub(re.compile("/src|/data/*|/output/*|/config"),"",os.getcwd())
today = datetime.today().strftime('%Y%m%d_%H%M%S')
file_out = f"{rootdir}/output/plots/pricehistory_plot_sum_{today}.html"

# pricehistoryfiles = ["./pricehistory/price_history_3ED_all.csv", "./pricehistory/price_history_ALL_all.csv", "./pricehistory/price_history_ICE_all.csv"]
# load list of price history files generated with get_prices.py
list_df_pricehistory = [pd.read_csv(pricehistoryfile, sep=",") for pricehistoryfile in args.pricehistoryfiles]

dict_df_total = {}
# remove and clip values to keep plot readable
for k in range(len(list_df_pricehistory)):
    cardnames = list(filter(lambda column: column != "date", list_df_pricehistory[k].columns))
    for cardname in cardnames:
        list_df_pricehistory[k][cardname].where(cond=list_df_pricehistory[k][cardname] < args.remove, other = np.nan, inplace=True)
        list_df_pricehistory[k][cardname].clip(upper=args.clip, inplace=True)
    if args.fillmissingvalues:
        # to fill missing values, carry forward previous known values
        list_df_pricehistory[k].fillna(method="ffill", inplace=True)
    df_total_tmp = pd.DataFrame({"_TOTAL_" + args.pricehistoryfiles[k] : list_df_pricehistory[k].sum(axis=1, numeric_only=True)})
    df_total_tmp.index = list_df_pricehistory[k]["date"]
    dict_df_total[args.pricehistoryfiles[k]] = df_total_tmp

df_total = pd.concat(dict_df_total, axis=1, ignore_index= True, join="outer")
df_total.columns = args.pricehistoryfiles

df_total["_TOTAL_ALL"] = df_total.sum(axis=1, numeric_only=True) 

#df_total["date"] = pd.to_datetime(df_total.index)
df_total["date"] = df_total.index
df_total["datetime"] = pd.to_datetime(df_total.index)
df_total.sort_values(by="datetime")
df_total.drop(labels="datetime", axis=1, inplace=True )

# make chart
df_total_long = df_total.melt(
    id_vars =  "date", 
    var_name="set", 
    value_name="price")

# add interactivity
selection = alt.selection_multi(fields=["set"], bind="legend")

lineplot = alt.Chart(df_total_long).mark_line().encode(
   x=alt.X('date:N', axis=alt.Axis(values=[df_total_long["date"][i] for i in range(0,df_total_long.shape[0],int(df_total_long.shape[0]/50))])),
   y= alt.Y("price:Q", axis=alt.Axis(orient="right"), scale=alt.Scale(type='log', base=10)) if args.log10 else alt.Y("price:Q", axis=alt.Axis(orient="right")), 
   color=alt.Color("set:N", legend = alt.Legend(symbolLimit = len(cardnames)+1)),
   opacity=alt.condition(selection, alt.value(1), alt.value(0.1))
).properties(
   height=int(args.width/3), width=args.width
).add_selection(
   selection
)

lineplot.save(file_out)