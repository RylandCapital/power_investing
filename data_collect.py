import requests
import pandas as pd
import numpy as np
from multiprocessing import Pool
import math
import time
#import schedule

'''get filtered list of US stocks using exchange and type'''
us_stocks = requests.get("https://eodhistoricaldata.com/api/exchange-symbol-list/US?api_token=5f3e88ded83498.58125490&fmt=json")
us_stocks = us_stocks.json()
us_stocks = pd.DataFrame.from_dict(us_stocks)  
universe = us_stocks[us_stocks['Exchange'].isin(['NYSE','NYSE ARCA',
                              'NASDAQ','NYSE MKT','BATS', 'AMEX',
                              ])]
universe = universe[universe['Type'].isin(['Common Stock'])]

wb = pd.ExcelFile(r'P:\11_CWP Alternative\cwp alt\research' + \
                             r'\power_investing\breakdown.xlsx')
sheetnames = wb.sheet_names

ag_etf_dict = {}
master_etf_list = []
for i in sheetnames:
    try:
        #this is ETF unverses given by Tommy
        uverse = pd.read_excel(r'P:\11_CWP Alternative\cwp alt\research' + \
                             r'\power_investing\breakdown.xlsx',
                             sheet_name=i, header=None)[0].tolist()
        ag_etf_dict[i] = uverse
        for i in uverse:
            master_etf_list.append(i)
    except:
        pass


etfs_and_stocks =  universe['Code'].tolist() #master_etf_list #
etfs_and_stocks = [i for i in etfs_and_stocks if i.find('-') == -1]  
etfs_and_stocks = [i for i in etfs_and_stocks if i.find('\\') == -1] 
etfs_and_stocks = [i for i in etfs_and_stocks if i.find('/') == -1] 
etfs_and_stocks = [i for i in etfs_and_stocks if i.find(' ') == -1] 
etfs_and_stocks = [i for i in etfs_and_stocks if i.find('  ') == -1] 
etfs_and_stocks = [i for i in etfs_and_stocks if i.find('?') == -1] 

cores = 6
stocks_available = len(etfs_and_stocks)
weeks_core = math.ceil(len(etfs_and_stocks)/cores)
week_ranges = np.arange(0,stocks_available+weeks_core,weeks_core)
ranges = [etfs_and_stocks[week_ranges[i]:week_ranges[i+1]] for i in np.arange(
        len(week_ranges)-1)]

symbols_ran = []

'''Stock Data Collection/Trading View Chart Data Collection'''
def pull_data(x):

    for i in x:
        
        symbols_ran.append(x)
        try:
             
            req = requests.get('https://eodhistoricaldata.com/api/eod/{0}.US?api_token=5f3e88ded83498.58125490&period=d&fmt=json'.format(i))
            ohlc = req.json()
            ohlc = pd.DataFrame.from_dict(ohlc)
            if len(ohlc)>0:
                 
            
                req2 = requests.get('https://eodhistoricaldata.com/api/fundamentals/{0}.US?api_token=5f3e88ded83498.58125490'.format(i))
                mc = req2.json()
                mc = pd.DataFrame.from_dict(mc)
                
        
            
                mcap = mc.loc['MarketCapitalization', 'Highlights']
                delisted = mc.loc['IsDelisted', 'General']
                exchange = mc.loc['Exchange', 'General']
                gicgroup = mc.loc['GicGroup', 'General']
                gicindustry = mc.loc['GicIndustry', 'General']
                gicsubindustry = mc.loc['GicSubIndustry', 'General']
                gicsector = mc.loc['GicSector', 'General']
                     
                
                ohlc = pd.DataFrame.from_dict(ohlc)
                ohlc['symbol'] = i
                ohlc['subindustry'] = gicsubindustry
                ohlc['industry'] = gicindustry
                ohlc['group'] = gicgroup
                ohlc['sector'] = gicsector
                ohlc['exchange'] = exchange
                ohlc['mc'] = mcap
                ohlc['delisted'] = delisted
                ohlc = ohlc[['date', 'symbol', 'open', 'high', 'low', 'close',
                              'adjusted_close', 'volume', 'subindustry', 'industry',
                              'group', 'sector', 'exchange', 'mc', 'delisted']]
                 #get name
                name = mc.loc['Name']['General']
                 
                ohlc['name'] = name
                 
                ohlc.to_csv(r'P:\11_CWP Alternative\cwp alt\research\power_investing\master\{0}.csv'.format(i))
            else:
                ohlc.to_csv(r'P:\11_CWP Alternative\cwp alt\research\power_investing\master\nodata\{0}nodata.csv'.format(i))
        except:
            ohlc.to_csv(r'P:\11_CWP Alternative\cwp alt\research\power_investing\master\errors\{0}exception.csv'.format(i))




def pull_etfs(x):  
    for i in x:         
            try:
                 req = requests.get('https://eodhistoricaldata.com/api/eod/{0}.US?api_token=5f3e88ded83498.58125490&period=d&fmt=json'.format(i))
                 ohlc = req.json()
                     
             
                 ohlc = pd.DataFrame.from_dict(ohlc)
                 ohlc['symbol'] = i
                 ohlc = ohlc[['date', 'symbol', 'open', 'high', 'low', 'close',
                              'adjusted_close', 'volume']]
                 
                 #get name
                 req2 = requests.get('https://eodhistoricaldata.com/api/fundamentals/{0}.US?api_token=5f3e88ded83498.58125490'.format(i))
                 mc = req2.json()
                 mc = pd.DataFrame.from_dict(mc)
                 name = mc.loc['Name']['General']
                 
                 ohlc['name'] = name
                 
                 ohlc.to_csv(r'P:\11_CWP Alternative\cwp alt\research\power_investing\master\{0}.csv'.format(i))

                 
                 
            except:
                try:
                    ohlc.to_csv('P:\\11_CWP Alternative\\cwp alt\\research\\power_investing\\master\\etferrors\\{0}.csv'.format(i))
                except:
                    ohlc.to_csv('P:\\11_CWP Alternative\\cwp alt\\research\\power_investing\\master\\etferrors\\{0}name_error.csv'.format(i))
                    
            
 
if __name__ == "__main__":
    
        start_time = time.time()
        pool = Pool(processes=cores)
        pool.map(pull_etfs, ranges)
        pool.close()
        pool.join() 
        print("--- %s seconds ---" % (time.time() - start_time)) 
    
#def run():
#    start_time = time.time()
#    pool = Pool(processes=cores)
#    pool.map(pull_data, ranges)
#    pool.close()
#    pool.join() 
#    print("--- %s seconds ---" % (time.time() - start_time)) 
#    
#schedule.every().day.at("13:10").do(run)
#
#while True:
#    schedule.run_pending()
#    time.sleep(60) # wait one minute
##        
#    
#    
    
    
    
    
    
    
    
    
    
    
    
    
#%%   
