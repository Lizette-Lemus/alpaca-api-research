from alpaca_trade_api.stream import Stream
from alpaca_trade_api.rest import TimeFrame
from datetime import datetime
import alpaca_trade_api as tradeapi
import logging
import numpy as np
from sklearn.linear_model import LinearRegression
import pandas as pd

logging.basicConfig(filename="log.txt", level=logging.INFO)
logging.info("Info logging test...")

#Read credentials
with open("/home/lizette/repos/alpaca-api-research/credentials.txt", "r") as f:
    lines = f.readlines()
    API_KEY = lines[0][:-1]
    API_SECRET = lines[1][:-1]
        

# instance of data streaming API
alpaca_stream = Stream(API_KEY, API_SECRET)
APCA_API_BASE_URL = "https://paper-api.alpaca.markets"
alpaca_trade = tradeapi.REST(API_KEY, API_SECRET, APCA_API_BASE_URL, api_version = "v2")

 # Define dictionary to organize our data
data = {}
 
def synch_datafeed(bar):
    # convert bar timestamp to human readable form
    time = datetime.fromtimestamp(bar.timestamp / 1000000000)
    symbol = bar.symbol

    # If we’ve never seen this timestamp before
    if time not in data:
       # Store bar data in a dictionary keyed by symbol and wait for data from the other symbol
       data[time] = {symbol:bar}
       return

    # If we’ve reached this point, then we have data for both symbols for the current timestamp
    data[time][symbol] = bar

    # retrieve dictionary containing bar data from a single timestamp
    timeslice = data[time]

    # pass that data into our next function for processing
    on_synch_data(timeslice)

async def on_equity_bar(bar):
    # bar data passed to intermediary function
    synch_datafeed(bar)

def rebalance_position():
    spy = alpaca_trade.get_bars("SPY", TimeFrame.Minute, "2022-06-01", "2023-01-17").df
    tlt = alpaca_trade.get_bars("TLT", TimeFrame.Minute, "2022-06-01", "2023-01-17").df 
    print(spy.head())
    print(tlt.head())
    data = pd.DataFrame()
    data['spy_close'] = spy['close']
    data['tlt_close'] = tlt['close']
    data.dropna(inplace = True)
    model = LinearRegression().fit(data['tlt_close'].values.reshape((-1, 1)), data['spy_close'].values)
    intercept = model.intercept_
    global slope, mean, std
    slope = model.coef_[0]
    print("slope:", slope)
    data['spread'] = data['spy_close'] - slope*data['tlt_close']
    mean = np.mean(data['spread'])
    std = np.std(data['spread'])
    print("mean:", mean)
    print("std:",  std)
    return

def get_slope():
    return 1.2176

def get_mean_std():
    mean = 259.15
    std = 14.099
    return mean, std

def on_synch_data(data):
    # access bar data
    spy_data = data["SPY"]
    tlt_data = data["TLT"]
    # save reference of close data for each bar
    spy_close = spy_data.close
    tlt_close = tlt_data.close
    print("spy_close:", spy_close)
    print("tlt_close:", tlt_close)
    # pass spread and level data to next part for placing trades
    place_trades(spy_close, tlt_close)

def place_trades(spy_close, tlt_close):
    active_position = len(alpaca_trade.list_positions()) != 0    
    print("active position", active_position)
    
    # calculate spread 
    spread = spy_close - slope*tlt_close
    print("slope*tlt_close:", slope*tlt_close)
    
    # we will use the z_score of the spread
    # calculate entry and exit levels for standard deviation
    entry_level = 0.9
    loss_exit_level = 3

    z_score = (spread - mean)/std
    # there is an active position if there is at least 1 position
    print("spread", spread)
    print("z score:", z_score)
    print("entry level:", entry_level)
    logging.info(f"z score: {z_score}")
    capital = 2000
    #case when z score > entry level
    spy_qty = int(capital/spy_close)
    tlt_qty = int(slope*spy_qty)
    
    #Going short
    if z_score > entry_level and z_score < entry_level + 0.5 and not active_position:
        print("placing long order on tlt")
        logging.info("placing long order on tlt")
        alpaca_trade.submit_order(symbol="TLT", qty=tlt_qty, type='market', side='buy', time_in_force='day')
        print("placing short order on spy")
        logging.info("placing short order on spy")
        alpaca_trade.submit_order(symbol="SPY", qty=spy_qty, type='market', side='sell', time_in_force='day')
    #going long
    elif z_score < -entry_level  and z_score > -entry_level - 0.5 and not active_position:
        print("placing short order on tlt")
        logging.info("placing short order on tlt")
        alpaca_trade.submit_order(symbol="TLT", qty=tlt_qty, type='market', side='sell', time_in_force='day')
        print("placing long order on spy")
        logging.info("placing long order on spy")
        alpaca_trade.submit_order(symbol="SPY", qty=spy_qty, type='market', side='buy', time_in_force='day')

    elif (z_score > loss_exit_level or z_score < -loss_exit_level)  and active_position:
        print("liquidating at loss exit level")
        logging.info("liquidating at loss exit level")
        #liquidate if loss exit level is breached
        alpaca_trade.close_all_positions()

    elif z_score < .1 and z_score > -0.1 and active_position:
        # liquidate if 0 spread is crossed with an active position
        print("closing at 0 z-score $$$") 
        logging.info("closing at 0 z-score $$$") 
        alpaca_trade.close_all_positions()
    print(" ")
    logging.info(" ")
     
def main():
    rebalance_position()
    alpaca_stream.subscribe_bars(on_equity_bar, "TLT")
    alpaca_stream.subscribe_bars(on_equity_bar, "SPY")

    # start streaming of data
    alpaca_stream.run()

if __name__ == "__main__":
    main()
