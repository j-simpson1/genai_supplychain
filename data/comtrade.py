
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import comtradeapicall
import os

subscription_key = os.getenv("COMTRADE_API_KEY") # comtrade api subscription key (from comtradedeveloper.un.org)
directory = '<OUTPUT DIR>'  # output directory for downloaded files

# Call get tariffline data API to a data frame, max to 250K records, free/premium subscription key required
# This example: imports of the assigned commodity_code (below) so that we can calculate the global unit value ($/kg)

Commodity_code = '3006' #pharmaceutical goods
Commodity_code = '1006' #rice
Commodity_code = '7108' #non-monetary gold
Commodity_code = '9201' #piano
Commodity_code = '2709' #crude oil
Commodity_code = '0901' #coffee
Commodity_code = '6309' #secondhand/ worn clothing
Commodity_code = '1001' #wheat and meslin

# create an Empty DataFrame object
panDForig = pd.DataFrame()
# A list of periods (this is for monthly sets), this is to optimize the API calls and avoid timeout
period_start = '2019-01-01'
period_end = '2022-12-01'
periods = pd.date_range(period_start,period_end,
              freq='MS').strftime("%Y%m").tolist()

# convert periods list into string with comma delimiter
delim = ","
temp = list(map(str, periods))
period_string = delim.join(temp)
print(period_string)

# get all tariffline data for a specific commodity_code
# this is a long operation and it is better to use comtradeapicall._getTarifflineData instead of comtradeapicall.getTarifflineData
# the function will split the query into multiple API calls reducing risk of timeout and increasing response time
panDForig = comtradeapicall._getTarifflineData(subscription_key, typeCode='C', freqCode='M', clCode='HS',
                                             period=period_string,
                                             reporterCode=None, cmdCode=Commodity_code, flowCode='M',
                                             partnerCode=None, partner2Code=None, customsCode=None, motCode=None, maxRecords=None,
                                             format_output='JSON',
                                             countOnly=None, includeDesc=True)

#check number of records
print('Final row count is:', len(panDForig))

#convert period to string for better viz
panDForig['period'] = panDForig['period'].astype('string')
panDForig['motCode'] = panDForig['motCode'].astype('string')
print(panDForig.info())

 #show some records
panDForig.head()

#some descriptive stats
panDForig[['primaryValue','netWgt']].describe()

#add new column UVnetWgt = primaryValue/netWgt
panDForig['UVnetWgt'] = panDForig.primaryValue / panDForig.netWgt

#remove UVnetWgt NaN,zero, inf, but and keeping only mode of transport and period
panDF = panDForig[["motDesc","period","UVnetWgt"]]
panDF = panDF[panDF.notnull()].query('UVnetWgt>0')
panDF = panDF[panDF.notnull()].query('UVnetWgt<999999999999999')
panDF.describe()

 # plot the Unit Value histogram
panDF.hist("UVnetWgt");
plt.xlabel('Unit Value ($/kg)')
plt.ylabel('# of trade data')
plt.title('Unit Value Distribution')

# plot the Unit Value histogram - in log scale (more suited for trade data with long distribution tail)
panDF.hist("UVnetWgt", log=True);
plt.xlabel('(log) Unit Value ($/kg)')
plt.ylabel('# of trade data')
plt.title('Unit Value Distribution')

#add log UVnetWgtLog
panDF.loc[:,'UVnetWgtLog'] = np.log(panDF['UVnetWgt'])
panDF.describe()

#remove outliers based on zcores (if more than 3 standard deviation) on the log Unit Value
from scipy.stats import zscore
#calculate z-scores of `df`
z_scores = zscore(panDF['UVnetWgtLog'], axis=0)
#print(z_scores)
abs_z_scores = np.abs(z_scores)
#print(abs_z_scores)
filtered_entries = (abs_z_scores < 3)
#print(filtered_entries)
new_panDF = panDF[filtered_entries]

# descriptive statistics after outliers removal
new_panDF.describe()

#histogram statistics after outliers removal
new_panDF.hist(column=['UVnetWgt','UVnetWgtLog'])

#plot median in timeseries after outliers removal
new_panDF[['period','UVnetWgt']].groupby("period").median().plot()

#plot median by mode of transport after outliers removal
new_panDF[['motDesc','UVnetWgt']].groupby("motDesc").median().sort_values(by='UVnetWgt').plot.bar(y='UVnetWgt', rot=90)

#some extra analysis  - descriptive statstiscs by period
new_panDF[['period','UVnetWgt']].groupby("period").describe()

#some extra analysis - descriptive statstiscs by motOfTransport (air, water,land)
new_panDF[['motDesc','UVnetWgt']].groupby("motDesc").describe()