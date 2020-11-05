import requests
import pandas as pd
import numpy as np
from os import listdir
from os.path import isfile, join
import matplotlib.pyplot as plt
from trading_calendars import get_calendar
import pymongo
     
df = pd.read_csv(r'P:\11_CWP Alternative\cwp alt\research\GICS.csv',index_col=0)
GICS_data = df.to_json()


'''Functions'''

def newhlDiff(df, lookback, pct=False):
    
    df = df.reset_index(drop=True)
    yearhigh = df.groupby('symbol')['adjusted_close'].rolling(lookback).max(
            ).reset_index()[['adjusted_close']]
    yearhigh.rename(columns={'adjusted_close':'yearhigh'}, inplace = True)
    yearlow = df.groupby('symbol')['adjusted_close'].rolling(lookback).min(
            ).reset_index()[['adjusted_close']]
    yearlow.rename(columns={'adjusted_close':'yearlow'}, inplace = True)
    closetm1 = df.groupby('symbol')['adjusted_close'].shift(1).reset_index(
            )[['adjusted_close']]
    closetm1.rename(columns={'adjusted_close':'closetm1'}, inplace = True)
    
    yeardf = yearhigh.join(yearlow).join(closetm1)
    
    df = df.join(yeardf).sort_index()
    
    df['new_high'] = np.where((df['adjusted_close'] >= df['yearhigh']) & \
      (df['closetm1'] < df['yearhigh']), 1, 0)
    df['new_low'] = np.where((df['adjusted_close'] <= df['yearlow']) & \
      (df['closetm1'] > df['yearlow']), 1, 0)
    
    if pct==False:
        newhighs = df.groupby('date')['new_high'].sum()
        newlows = df.groupby('date')['new_low'].sum()
    else:
        num_holdings = len(df['symbol'].unique())
        newhighs = df.groupby('date')['new_high'].sum()/num_holdings
        newlows = df.groupby('date')['new_low'].sum()/num_holdings
        
    differential = newhighs-newlows
    
    return differential

def advdecDiff(df, pct=False):
    
    df = df.reset_index()
    closetm1 = df.groupby('symbol')['adjusted_close'].shift(1).reset_index(
            )[['adjusted_close']]
    closetm1.rename(columns={'adjusted_close':'closetm1'}, inplace = True)
    df = df.join(closetm1)
    df['adv_issues'] = np.where(df['adjusted_close']>df['closetm1'],1,0)
    df['dec_issues'] = np.where(df['adjusted_close']<df['closetm1'],1,0)

    if pct==False:
        advancers = df.groupby('date')['adv_issues'].sum()
        decliners = df.groupby('date')['dec_issues'].sum()
    else:
        num_holdings = len(df['symbol'].unique())
        advancers = df.groupby('date')['adv_issues'].sum()/num_holdings
        decliners = df.groupby('date')['dec_issues'].sum()/num_holdings
        
    differential = advancers-decliners
    
    return differential

def smaBreadth(df, lookback, pct=False):
    
    df = df.reset_index()
    sma = df.groupby('symbol')['adjusted_close'].rolling(
            lookback).mean().reset_index()[['adjusted_close']]
    sma.rename(columns={'adjusted_close':'sma'}, inplace = True)
    df = df.join(sma)
    df['sma_breadth'] = np.where(df['adjusted_close']>df['sma'],1,0)

    if pct==False:
        sma = df.groupby('date')['sma_breadth'].sum()
    else:
        num_holdings = len(df['symbol'].unique())
        sma = df.groupby('date')['sma_breadth'].sum()/num_holdings
        
    return sma

def mclellanDiff(df, pct=True):
    
    advdec = advdecDiff(df, pct=pct)
    
    differential = advdec.ewm(span=19).mean() - \
    advdec.ewm(span=39).mean()
    
    return differential

def breadthThrust(df):
    
    df = df.reset_index()
    closetm1 = df.groupby('symbol')['adjusted_close'].shift(1).reset_index(
            )[['adjusted_close']]
    closetm1.rename(columns={'adjusted_close':'closetm1'}, inplace = True)
    df = df.join(closetm1)
    df['adv_issues'] = np.where(df['adjusted_close']>df['closetm1'],1,0)
    df['dec_issues'] = np.where(df['adjusted_close']<df['closetm1'],1,0)

    advancers = df.groupby('date')['adv_issues'].sum()
    decliners = df.groupby('date')['dec_issues'].sum()
        
    thrust = advancers/(advancers+decliners)
    
    return thrust
    
    
def volumeAdv(df):
    
    df = df.reset_index()
    closetm1 = df.groupby('symbol')['adjusted_close'].shift(1).reset_index(
            )[['adjusted_close']]
    closetm1.rename(columns={'adjusted_close':'closetm1'}, inplace = True)
    df = df.join(closetm1)
    df['adv_issues'] = np.where(df['adjusted_close']>df['closetm1'],1,0)
    df['dec_issues'] = np.where(df['adjusted_close']<df['closetm1'],1,0)
    
    advdf = df[df['adv_issues'] == 1].groupby('date')['volume'].sum()
    decdf = df[df['dec_issues'] == 1].groupby('date')['volume'].sum()
    
    thrust =  advdf/(advdf+decdf)
    
    return thrust

def volumeDec(df):
    
    df = df.reset_index()
    closetm1 = df.groupby('symbol')['adjusted_close'].shift(1).reset_index(
            )[['adjusted_close']]
    closetm1.rename(columns={'adjusted_close':'closetm1'}, inplace = True)
    df = df.join(closetm1)
    df['adv_issues'] = np.where(df['adjusted_close']>df['closetm1'],1,0)
    df['dec_issues'] = np.where(df['adjusted_close']<df['closetm1'],1,0)
    
    advdf = df[df['adv_issues'] == 1].groupby('date')['volume'].sum()
    decdf = df[df['dec_issues'] == 1].groupby('date')['volume'].sum()
    
    thrust =  decdf/(advdf+decdf)
    
    return thrust
    
def equalweight(df):

    equalweight = (1+df.groupby('date')['pct_change'].mean()).cumprod()
    
    return equalweight


def agGrid(master, etf_list, mongo_call):
     
    masterag = master[master['symbol'].isin(etf_list)]
    masterg =  masterag.groupby('symbol')
    masterag['pct_change'] = (masterg['adjusted_close'] \
            .pct_change()*100).round(2)
    masterag['pct_changeW'] = (masterg['adjusted_close'] \
            .pct_change(periods=5)*100).round(2)
    masterag['pct_changeM'] = (masterg['adjusted_close'] \
            .pct_change(periods=21)*100).round(2)
    masterag['pct_changeQ'] = (masterg['adjusted_close'] \
            .pct_change(periods=63)*100).round(2)
    
    ags = []
    for i in masterag['symbol'].unique():
        i = masterag[masterag['symbol'] == i]
        try:
            i['rsdf253'] = ((i['adjusted_close'].pct_change(periods=252))*.2) + \
            ((i['adjusted_close'].pct_change(periods=189))*.2) + \
            ((i['adjusted_close'].pct_change(periods=126))*.2) + \
            ((i['adjusted_close'].pct_change(periods=63))*.4)
            i['rsdf253-5'] = i['rsdf253'].shift(5)
            i['rsdf253-21'] = i['rsdf253'].shift(21)
            i['rsdf253-63'] = i['rsdf253'].shift(63)
            
            i['rsdf126'] = ((i['adjusted_close'].pct_change(periods=126))*.2) + \
            ((i['adjusted_close'].pct_change(periods=96))*.2) + \
            ((i['adjusted_close'].pct_change(periods=64))*.2) + \
            ((i['adjusted_close'].pct_change(periods=32))*.4)
            i['rsdf126-5'] = i['rsdf126'].shift(5)
            i['rsdf126-21'] = i['rsdf126'].shift(21)
            i['rsdf126-63'] = i['rsdf126'].shift(63)
            
            i['rsdf63'] = ((i['adjusted_close'].pct_change(periods=63))*.2) + \
            ((i['adjusted_close'].pct_change(periods=48))*.2) + \
            ((i['adjusted_close'].pct_change(periods=32))*.2) + \
            ((i['adjusted_close'].pct_change(periods=16))*.4)
            i['rsdf63-5'] = i['rsdf63'].shift(5)
            i['rsdf63-21'] = i['rsdf63'].shift(21)
            i['rsdf63-63'] = i['rsdf63'].shift(63)
            
            i['close-26wma'] = i['adjusted_close'] / \
            i['adjusted_close'].rolling(126).mean()
            
            ags.append(i)
        except:
            print('error')
            pass
    
    aggrid = pd.concat(ags)
    
    aggrid = pd.concat(ags)[['date', 'name','symbol', 'close', 'pct_change',
                     'pct_changeW', 'pct_changeM', 'pct_changeQ', 'rsdf63', 'rsdf63-5',
                     'rsdf63-21', 'rsdf63-63', 'close-26wma']]

    aggrid = aggrid.groupby('symbol').last().reset_index()
    
    aggrid.loc[:,'rsdf63'] = aggrid.loc[:,'rsdf63'].rank(
            pct=True).round(2)*100-1
    aggrid.loc[:,'rsdf63-5'] = aggrid.loc[:,'rsdf63-5'].rank(
            pct=True).round(2)*100-1
    aggrid.loc[:,'rsdf63-21'] = aggrid.loc[:,'rsdf63-21'].rank(
            pct=True).round(2)*100-1
    aggrid.loc[:,'rsdf63-63'] = aggrid.loc[:,'rsdf63-63'].rank(
            pct=True).round(2)*100-1
    aggrid['RS_Movers'] = aggrid['rsdf63'] - aggrid['rsdf63-5']
    aggrid['RS_Movers_21'] = aggrid['rsdf63'] - \
        aggrid['rsdf63-21']
    aggrid['close-26wma'] = aggrid['close-26wma'].round(2)
    
    aggrid.columns = ['Symbol', 'date', 'Description', 'Close', 'Daily%',
                         'Week%', 'Mo%', 'Qtr%', 'RS', 'RS-5', 'RS-21', 'RS-63',
                         '26wmaRS', 'RSMovers', 'RSMovers-21']
    aggrid = aggrid[['Description',  'date', 'Symbol', 'Close', 'Daily%',
                         'Week%', 'Mo%', 'Qtr%', 'RS', 'RS-5', 'RS-21', 'RS-63',
                         '26wmaRS', 'RSMovers', 'RSMovers-21']]
    
    
    
    collection = mongo_call
    collection.drop()
    collection.insert_many(aggrid.to_dict(orient='records'))
    
    return aggrid

'''GICS'''
unique_exchange = df['Exchange'].unique()
unique_sectorcode = df['GicSector'].unique()
unique_groupcode = df['GicGroup'].unique()
unique_industrycode = df['GicIndustry'].unique()
unique_subindustrycode = df['GicSubIndustry'].unique()
unique_GicSector = df['GicSector.1'].unique()
unique_GicGroup = df['GicGroup.1'].unique()
unique_GicIndustry = df['GicIndustry.1'].unique()
unique_GicSubIndustry = df['GicSubIndustry.1'].unique()

exchangedfs = []
exchange_dict = {}
for i in unique_exchange:
   tickers = df[df['Exchange'] == i].index.values
   for t in tickers:
       exchange_dict[t] = i
   exchangedf = pd.DataFrame(tickers, columns=[i])
   exchangedfs.append(exchangedf) 

sectorcodedfs = []
sectorcode_dict = {}
for i in unique_sectorcode:
   tickers = df[df['GicSector'] == i].index.values
   for t in tickers:
       sectorcode_dict[t] = i
   sectorcodedf = pd.DataFrame(tickers, columns=[i])
   sectorcodedfs.append(sectorcodedf)    
   
groupcodedfs = []
groupcode_dict = {}
for i in unique_groupcode:
   tickers = df[df['GicGroup'] == i].index.values
   for t in tickers:
       groupcode_dict[t] = i
   groupcodedf = pd.DataFrame(tickers, columns=[i])
   groupcodedfs.append(groupcodedf) 
   
industrycodedfs = []
industrycode_dict = {}
for i in unique_industrycode:
   tickers = df[df['GicIndustry'] == i].index.values
   for t in tickers:
       industrycode_dict[t] = i
   industrycodedf = pd.DataFrame(tickers, columns=[i])
   industrycodedfs.append(industrycodedf) 
   
subindustrycodedfs = []
subindustrycode_dict = {}
for i in unique_subindustrycode:
   tickers = df[df['GicSubIndustry'] == i].index.values
   for t in tickers:
       subindustrycode_dict[t] = i
   subindustrycodedf = pd.DataFrame(tickers, columns=[i])
   subindustrycodedfs.append(subindustrycodedf) 

  
sectordfs = []
sector_dict = {}
names = []
lengths = []
for i in unique_GicSector:
   tickers = df[df['GicSector.1'] == i].index.values
   for t in tickers:
       sector_dict[t] = i
   sectordf = pd.DataFrame(tickers, columns=[i])
   names.append(i)
   lengths.append(len(sectordf))
   sectordfs.append(sectordf)
   
 
pd.DataFrame([names, lengths]).T.to_csv(r'C:\Users\rmathews\Downloads\sector.csv')
   
groupdfs = []
group_dict = {}
names = []
lengths = []
for i in unique_GicGroup:
   tickers = df[df['GicGroup.1'] == i].index.values
   for t in tickers:
       group_dict[t] = i
   groupdf = pd.DataFrame(tickers, columns=[i])
   names.append(i)
   lengths.append(len(groupdf))
   groupdfs.append(groupdf)
    
pd.DataFrame([names, lengths]).T.to_csv(r'C:\Users\rmathews\Downloads\group.csv')


industrydfs = []
industrydfs_dict = {}
for i in unique_GicIndustry:
   tickers = df[df['GicIndustry.1'] == i].index.values
   for t in tickers:
       industrydfs_dict[t] = i
   industrydf = pd.DataFrame(tickers, columns=[i])
   industrydfs.append(industrydf)
   
subindustrydfs = []
for i in unique_GicSubIndustry:
 tickers = df[df['GicSubIndustry.1'] == i].index.values
 subindustrydf = pd.DataFrame(tickers, columns=[i])

 subindustrydfs.append(subindustrydf)

'''Get All ETFs needed for site'''
wb = pd.ExcelFile(r'C:\Users\rmathews\Desktop\WPy64-3740' + \
                         r'\scripts\rcaresearch\breakdown.xlsx')
sheetnames = wb.sheet_names

ag_etf_dict = {}
master_etf_list = []
for i in sheetnames:
    try:
        uverse = pd.read_excel(r'C:\Users\rmathews\Desktop\WPy64-3740' + \
                             r'\scripts\rcaresearch\breakdown.xlsx',
                             sheet_name=i, header=None)[0].tolist()
        ag_etf_dict[i] = uverse
        for i in uverse:
            master_etf_list.append(i)
    except:
        pass
 
 #%% 
'''Stock Data Collection/Trading View Chart Data Collection'''
#subindustries
api_errors = []
for i in subindustrydfs:
    subindustry = i.columns[0]
    print(subindustry)
    for stock in i[subindustry]:
         print(stock)
         try:
             req = requests.get('https://eodhistoricaldata.com/api/eod/{0}.US?api_token=5f3e88ded83498.58125490&period=d&fmt=json'.format(stock))
             ohlc = req.json()
                 
             try:
                 req2 = requests.get('https://eodhistoricaldata.com/api/fundamentals/{0}.US?api_token=5f3e88ded83498.58125490'.format(stock))
                 mc = req2.json()
                 mc = pd.DataFrame.from_dict(mc).loc['MarketCapitalization', 'Highlights']
             except:
                 print('no mc')
                 mc=50000000
             
             ohlc = pd.DataFrame.from_dict(ohlc)
             ohlc['symbol'] = stock
             ohlc['subindustry'] = subindustry
             ohlc['industry'] = industrydfs_dict[stock]
             ohlc['group'] = group_dict[stock]
             ohlc['sector'] = sector_dict[stock]
             ohlc['subindustrycode'] = subindustrycode_dict[stock]
             ohlc['industrycode'] = industrycode_dict[stock]
             ohlc['groupcode'] = groupcode_dict[stock]
             ohlc['sectorcode'] = sectorcode_dict[stock]
             ohlc['exchange'] = exchange_dict[stock]
             ohlc['mc'] = mc
             ohlc = ohlc[['date', 'symbol', 'open', 'high', 'low', 'close',
                          'adjusted_close', 'volume', 'subindustry', 'industry',
                          'group', 'sector', 'subindustrycode', 'industrycode',
                          'groupcode', 'sectorcode', 'exchange', 'mc']]
             ohlc.to_csv(r'C:\Users\rmathews\Desktop\WPy64-3740\scripts\rcaresearch\master\{0}.csv'.format(stock))
         except:
             ohlc = 'API ERROR'
             print('api error #1...trying again') 
             try:
                 req = requests.get('https://eodhistoricaldata.com/api/eod/{0}.US?api_token=5f3e88ded83498.58125490&period=d&fmt=json'.format(stock))
                 ohlc = req.json()
                 
              
                 try:
                     req2 = requests.get('https://eodhistoricaldata.com/api/fundamentals/A.US?api_token=5f3e88ded83498.58125490'.format(stock))
                     mc = req2.json()
                     mc = pd.DataFrame.from_dict(mc).loc['MarketCapitalization', 'Highlights']
                 except:
                     print('no mc')
                     mc=50000000
            
                 ohlc = pd.DataFrame.from_dict(ohlc)
                 ohlc['symbol'] = stock
                 ohlc['subindustry'] = subindustry
                 ohlc['industry'] = industrydfs_dict[stock]
                 ohlc['group'] = group_dict[stock]
                 ohlc['sector'] = sector_dict[stock]
                 ohlc['subindustrycode'] = subindustrycode_dict[stock]
                 ohlc['industrycode'] = industrycode_dict[stock]
                 ohlc['groupcode'] = groupcode_dict[stock]
                 ohlc['sectorcode'] = sectorcode_dict[stock]
                 ohlc['exchange'] = exchange_dict[stock]
                 ohlc['mc'] = mc
                 ohlc = ohlc[['date', 'symbol', 'open', 'high', 'low', 'close',
                              'adjusted_close', 'volume', 'subindustry', 'industry',
                              'group', 'sector', 'subindustrycode', 'industrycode',
                              'groupcode', 'sectorcode', 'exchange', 'mc']]
                 ohlc.to_csv(r'C:\Users\rmathews\Desktop\WPy64-3740\scripts\rcaresearch\master\{0}.csv'.format(stock))
             except:
                api_errors.append(stock)
                ohlc = 'API ERROR'
                print('failed again')     
                

'''AG Grid ETF Data Collection'''
#etfs
api_errors = []
master_etf_list = []
for key in ag_etf_dict.keys():
    for stock in ag_etf_dict[key]:
         print(stock)
         try:
             req = requests.get('https://eodhistoricaldata.com/api/eod/{0}.US?api_token=5f3e88ded83498.58125490&period=d&fmt=json'.format(stock))
             ohlc = req.json()
                 
         
             ohlc = pd.DataFrame.from_dict(ohlc)
             ohlc['symbol'] = stock
             ohlc = ohlc[['date', 'symbol', 'open', 'high', 'low', 'close',
                          'adjusted_close', 'volume']]
             
             #get name
             req2 = requests.get('https://eodhistoricaldata.com/api/fundamentals/{0}.US?api_token=5f3e88ded83498.58125490'.format(stock))
             mc = req2.json()
             mc = pd.DataFrame.from_dict(mc)
             name = mc.loc['Name']['General']
             
             ohlc['name'] = name
             
             ohlc.to_csv(r'C:\Users\rmathews\Desktop\WPy64-3740\scripts\rcaresearch\master\{0}.csv'.format(stock))
             
             master_etf_list.append(stock)
             
         except:
             ohlc = 'API ERROR'
             print('api error #1...trying again') 
             try:
                 req = requests.get('https://eodhistoricaldata.com/api/eod/{0}.US?api_token=5f3e88ded83498.58125490&period=d&fmt=json'.format(stock))
                 ohlc = req.json()      
            
                 ohlc = pd.DataFrame.from_dict(ohlc)
                 ohlc['symbol'] = stock
                 ohlc = ohlc[['date', 'symbol', 'open', 'high', 'low', 'close',
                              'adjusted_close', 'volume']]
                 
                 req2 = requests.get('https://eodhistoricaldata.com/api/fundamentals/{0}.US?api_token=5f3e88ded83498.58125490'.format(stock))
                 mc = req2.json()
                 mc = pd.DataFrame.from_dict(mc)
                 name = mc.loc['Name']['General']
                 ohlc['name'] = name
                 
                 ohlc.to_csv(r'C:\Users\rmathews\Desktop\WPy64-3740\scripts\rcaresearch\master\{0}.csv'.format(stock))
             except:
                api_errors.append(stock)
                ohlc = 'API ERROR'
                print('failed again') 
#%%   
'''Data Manipulation for Tradingview and AG Grid'''

filter_list = pd.read_csv(r'C:\Users\rmathews\Desktop\WPy64-3740\scripts' + \
                          r'\rcaresearch\filtered_list.csv', 
                          header=None)[0].unique()
mypath = r'C:\Users\rmathews\Desktop\WPy64-3740\scripts\rcaresearch\master'
onlyfiles = [f for f in listdir(mypath) if isfile(join(mypath, f))]

master = pd.concat([pd.read_csv(mypath
                                + "\\" + i, index_col=0) for i in onlyfiles])
#cal filter 
calfilter = get_calendar('NYSE').sessions_in_range('2000-01-01', '2021-09-27')
calfilter = [pd.to_datetime(i.date()) for i in calfilter]
master = master[pd.to_datetime(master['date']).isin(calfilter)]
master_agetfs_only = master[master['symbol'].isin(master_etf_list)] 
master = master[master['symbol'].isin(filter_list)]
master['pct_change'] = master.groupby('symbol')['adjusted_close'].pct_change()

'''RUN FILTER CODE PERIDOCIALLY TO UPDATE FILTER LIST'''
'''Type Filter'''
#symbol_filter = pd.read_csv(r'C:\Users\rmathews\Desktop\WPy64-3740\scripts' + \
#                            r'\rcaresearch\symbol_filter.csv')
#symbol_filter['Type'].unique()
#exchange_filter = symbol_filter[symbol_filter['Exchange'].isin(['NYSE','NYSE ARCA',
#                              'NASDAQ','NYSE MKT','BATS', 'AMEX',
#                              'US'])]['Code'].tolist()
#type_filter = symbol_filter[symbol_filter['Type'].isin(['Common Stock',
#                            'ETF'])]['Code'].tolist()
#master = master[master['symbol'].isin(exchange_filter+type_filter)]
#
#'''price filter'''
#master['price_filter'] = np.where((master['adjusted_close']>=2) & \
#      (master['adjusted_close'].shift(1) >=2),1,0)
#
#'''volume filter'''
#master['volume_filter'] = np.where((master['volume']>=50000) & \
#      (master['volume'].shift(1)>=50000),1,0)

#master['symbol'].to_csv(r'C:\Users\rmathews\Desktop\WPy64-3740\scripts' + \
#      r'\rcaresearch\filtered_list.csv',index=False)


'''AGgrid 1 Calcs'''
client = pymongo.MongoClient("mongodb+srv://ryland:Chester53@syndicate-" + \
                        "uofbw.mongodb.net/test?retryWrites=true&w=majority")
db = client.pulses
db_names = [i.replace('&', '').replace(' ', '_').replace('__', '_').lower() \
            for i in list(ag_etf_dict.keys())]
db_names = [db.world,
 db.intermarket,
 db.size__style,
 db.cw_sector,
 db.ew_sector,
 db.sc_sector,
 db.materials,
 db.consumer_staples,
 db.consumer_discretionary,
 db.energy,
 db.financials,
 db.health_care,
 db.industrials,
 db.real_estate,
 db.information_technology,
 db.communication_services,
 db.utilities]

agGs = []
for key, n in zip(ag_etf_dict.keys(), db_names):
    try:
        agG = agGrid(master_agetfs_only , ag_etf_dict[key], n)
        agGs.append(agG)
        print('yeet me')
    except:
        pass
                
    

#%% 
'''Trading View Chart Calculations'''
client = pymongo.MongoClient("mongodb+srv://ryland:Chester53@syndicate-" + \
                        "uofbw.mongodb.net/test?retryWrites=true&w=majority")
db = client.pulses

grouping = ['sector']
groupdbs = [db.aggsector]
tempnames = [['Financials']]
masterdfs = []
for agg, aggdb, i in zip(grouping, groupdbs, tempnames):
    groupdfs = []
    i=i[0]
    temp = master[(master[agg]==i)]
    temp['date'] = pd.to_datetime(temp['date'])# & (master['price_filter'] == 1) &
                  #(master['volume_filter'] == 1)]
#    datetest = temp[(temp['date'] > pd.to_datetime('7/01/20')) & (temp['date'] < pd.to_datetime('8/1/20'))].sort_values(['symbol', 'date'])
    differential = newhlDiff(temp,253,pct=True)
    differential_advdec = advdecDiff(temp,pct=True)
    differential_advdeccum = advdecDiff(temp,pct=False).cumsum()
    sma_breadth20 = smaBreadth(temp, 20 ,pct=True)
    sma_breadth50 = smaBreadth(temp, 50 ,pct=True)
    sma_breadth200 = smaBreadth(temp, 200 ,pct=True)
    differential_mclellan = mclellanDiff(temp, pct=True)
    differential_mclellancum =  mclellanDiff(temp, pct=False).cumsum()
    differential_mclellancum10 = differential_mclellancum.rolling(10).mean()
    breadth_thrust = breadthThrust(temp) 
    volumeadv = volumeAdv(temp) 
    volumedec = volumeDec(temp) 
    equalweightdf = equalweight(temp)
    
    groupdf = pd.concat([differential,
                         differential_advdec,
                         differential_advdeccum,
                         sma_breadth20,
                         sma_breadth50,
                         sma_breadth200,
                         differential_mclellan,
                         differential_mclellancum,
                         differential_mclellancum10,
                         breadth_thrust,
                         volumeadv,
                         volumedec,
                         equalweightdf],axis=1)
    groupdf.columns = ['{1}_{0}_NH_NL253'.format(i.upper().replace(
                               ' ','_').replace(',','_'), agg.upper()),
                       '{1}_{0}_AD'.format(i.upper().replace(
                               ' ','_').replace(',','_'), agg.upper()),
                       '{1}_{0}_CUMULATIVE_AD'.format(i.upper().replace(
                               ' ','_').replace(',','_'), agg.upper()),
                       '{1}_{0}_SMA_BREADTH20'.format(i.upper().replace(
                               ' ','_').replace(',','_'), agg.upper()),
                       '{1}_{0}_SMA_BREADTH50'.format(i.upper().replace(
                               ' ','_').replace(',','_'), agg.upper()),
                       '{1}_{0}_SMA_BREADTH200'.format(i.upper().replace(
                               ' ','_').replace(',','_'), agg.upper()),
                       '{1}_{0}_MCLELLAN_OSC'.format(i.upper().replace(
                               ' ','_').replace(',','_'), agg.upper()),
                       '{1}_{0}_MCLELLAN_SUMM'.format(i.upper().replace(
                               ' ','_').replace(',','_'), agg.upper()),
                       '{1}_{0}_MCLELLAN_SUMM10'.format(i.upper().replace(
                               ' ','_').replace(',','_'), agg.upper()),
                       '{1}_{0}_BREATH_THRUST'.format(i.upper().replace(
                               ' ','_').replace(',','_'), agg.upper()),
                       '{1}_{0}_VOLUME_ADV'.format(i.upper().replace(
                               ' ','_').replace(',','_'), agg.upper()),
                       '{1}_{0}_VOLUME_DEC'.format(i.upper().replace(
                               ' ','_').replace(',','_'), agg.upper()),
                       '{1}_{0}_EQUALW_INDEX'.format(i.upper().replace(
                               ' ','_').replace(',','_'), agg.upper()),
                       ]
    groupdfs.append(groupdf)
    masterdfs.append(groupdf)
    
master_group = pd.concat(groupdfs, axis=1)
master_group = master_group.tz_localize('EST')

master_master = pd.concat(masterdfs, axis=1)
master_master = master_master.tz_localize('EST')

collection = db.agggroup
collection.drop()
collection.insert_many(master_master.reset_index().to_dict(orient='records'))

















