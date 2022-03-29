'''
plot price history for a set of MTG cards from mtggoldfish.com 

# usage:
poetry run python ./src/plot_prices.py  -s "," -p ./output/pricehistory/1990s_all_pricehist_20210619_220609.csv -r 300 -m 10 -i ./data/lists_sale/210702_mpilgaard_reserved1_mi.csv
'''
import os 
import pandas as pd 
import numpy as np
import argparse
import altair as alt
from datetime import datetime
import re 

# Initialize parser
parser = argparse.ArgumentParser(description='Download MTGgoldfish price history for a list of cards')

# Add parser arguments
parser.add_argument("-i", "--inputfile", dest="inputfile", type=str, help = "file with columns: card name, set code (see https://www.mtggoldfish.com/sets), grade as in config/grade.csv and number of cards")
parser.add_argument("-p","--pricehistoryfile",dest="pricehistoryfile",type=str, help = "pricehistory csv file containing at least columns that match card names in inputfile")
parser.add_argument("-s", "--sep", dest="sep", type=str, help = "file column separator for inputfile (default ,)", default=",")
parser.add_argument("-l", "--log10", dest="log10", type=bool, help = "plot y-axis on log10 scale. Useful for being able to make out lower prices when there are extremely high prices, (default False)", default=False)
parser.add_argument("-w", "--width", dest="width", type=int, help = "plot width in px (default 2000)", default="2000")
parser.add_argument("-f", "--fillmissingvalues", dest="fillmissingvalues", type=bool, help = "Carry forward last known value to fill missing values? (default True)", default=True)
parser.add_argument("-c", "--clip", dest="clip", type=int, help = "threshold at which to clip values (sets them to max)? int, (default 5000)", default=5000)
parser.add_argument("-r", "--remove", dest="remove", type=int, help = "threshold at which to remove values (sets them to max)? int, (default 10000)", default=10000)
parser.add_argument("-m", "--min_max_value", dest="min_max_value", type=float, help = "omit cards with a max value below this min_max_value", default=5)

# Read arguments from command line
args = parser.parse_args()

rootdir = re.sub(re.compile("/src|/data/*|/output/*|/config"),"",os.getcwd())
# today = datetime.today().strftime('%Y%m%d_%H%M%S')
inputfile_truncated = re.sub(re.compile(r'\.txt$|\.csv$|\.tsv$'),'',args.inputfile)
inputfile_truncated = re.sub(re.compile("^.*/"),"", inputfile_truncated)

file_out = f"{rootdir}/output/plots/{inputfile_truncated}_pricehistory_plot.html"

# load input file with magic card names and sets
df = pd.read_csv(args.inputfile, sep = args.sep)

df[df.columns[0]] = [el.lower() for el in df[df.columns[0]]]
df[df.columns[1]] = [el.lower() for el in df[df.columns[1]]]

df.sort_values(by=df.columns[0], inplace=True)
df.index = range(df.shape[0])
# load price history generated with get_prices.py
df_pricehistory = pd.read_csv(args.pricehistoryfile, sep=",")
df_pricehistory.columns = [el.lower() for el in df_pricehistory.columns]
df_grade = pd.read_csv(f"{rootdir}/config/grade.csv")


if not all([df[df.columns[0]][i].strip() + "_" + df[df.columns[1]][i].strip() in df_pricehistory.columns for i in range(df.shape[0])]): #
   list_name_set_missing = [df[df.columns[0]][i].strip() + "_" + df[df.columns[1]][i].strip() for i in range(df.shape[0]) if not df[df.columns[0]][i].strip() + "_" + df[df.columns[1]][i].strip() in df_pricehistory.columns]
   print("Warning: the following cards were not found in pricehistoryfile columns: {}".format(list_name_set_missing))
   df = df[[df[df.columns[0]][i].strip() + "_" + df[df.columns[1]][i].strip() in df_pricehistory.columns for i in range(df.shape[0])]]
   df.index = range(df.shape[0])

# make a plot 
list_name_set_grade_n = [{"name":df.at[i,df.columns[0]].strip(), "set":df.at[i,df.columns[1]].strip(), "grade": df.at[i,df.columns[2]].strip(), "n":df.at[i,df.columns[3]]} for i in range(df.shape[0])]
list_nameset = [obj["name"] + "_" + obj["set"]  for obj in list_name_set_grade_n]

# remove and clip values to keep plot readable
idx_rm=[]
for k in range(len(list_name_set_grade_n)):
   name_set = list_name_set_grade_n[k]["name"] + "_" + list_name_set_grade_n[k]["set"]
   df_pricehistory[name_set].where(cond=df_pricehistory[name_set] < args.remove, other = np.nan, inplace=True)
   df_pricehistory[name_set].clip(upper=args.clip, inplace=True)
   # take into account card grade
   idx_row_1 = [i for i, x in enumerate(df_grade["abbreviation"]==list_name_set_grade_n[k]["grade"]) if x][0]
   price_multiplier = df_grade.at[idx_row_1,"price_multiplier"]
   df_pricehistory[name_set + "_" + list_name_set_grade_n[k]["grade"] + " (" + str(list_name_set_grade_n[k]["n"]) + ")"] = df_pricehistory[name_set].multiply(price_multiplier)
   # filter out low value cards
   if df_pricehistory[name_set + "_" + list_name_set_grade_n[k]["grade"] + " (" + str(list_name_set_grade_n[k]["n"]) + ")"].max() < args.min_max_value:
         df_pricehistory.drop(labels=name_set + "_" + list_name_set_grade_n[k]["grade"] +  " (" + str(list_name_set_grade_n[k]["n"]) + ")", axis=1, inplace=True )
         bool_filter = [df[df.columns[0]][i] != name_set.split("_")[0] or df[df.columns[1]][i] != name_set.split("_")[1] for i in df.index]
         df=df[bool_filter]
         idx_rm.append(k)
list_name_set_grade_n = [list_name_set_grade_n[k] for k in range(len(list_name_set_grade_n)) if not k in idx_rm]
df.index = range(df.shape[0])

# to fill missing values, carry forward previous known values
if args.fillmissingvalues:
   df_pricehistory.fillna(method="ffill", inplace=True)

#if df.shape[1]>2: # if there is a third column  

df_pricehistory["_WEIGHTED_AVG"] = [sum([df_pricehistory[df[df.columns[0]][j] + "_" + df[df.columns[1]][j] + "_" + df[df.columns[2]][j] +  " (" + str(df[df.columns[3]][j]) + ")"][i] * df[df.columns[3]][j] for j in df.index])/sum(df[df.columns[3]]) for i in df_pricehistory.index]

# make chart
df_pricehistory_long = df_pricehistory.melt(
    value_vars = [obj["name"] + "_" + obj["set"] + "_" + obj["grade"] +  " (" + str(obj["n"])  + ")" for obj in list_name_set_grade_n] + ["_WEIGHTED_AVG"],
    id_vars = "date", 
    var_name="name", 
    value_name="price")

# add interactivity
selection = alt.selection_multi(fields=["name"], bind="legend")

n_cards_total = df[df.columns[3]].sum()
lineplot = alt.Chart(df_pricehistory_long, title=f"Price trends, n={n_cards_total} cards").mark_line().encode(
   x=alt.X('date:N', axis=alt.Axis(values=[df_pricehistory["date"][i] for i in range(0,df_pricehistory.shape[0],int(df_pricehistory.shape[0]/100))])),
   y= alt.Y("price:Q", axis=alt.Axis(orient="right"), scale=alt.Scale(type='log', base=10)) if args.log10 else alt.Y("price:Q", axis=alt.Axis(orient="right")), 
   color=alt.Color("name:N", legend = alt.Legend(symbolLimit = len(list_name_set_grade_n)+1)),
   opacity=alt.condition(selection, alt.value(1), alt.value(0.1))
).properties(
   height=int(args.width/3), width=args.width
).add_selection(
   selection
)

lineplot.save(file_out)