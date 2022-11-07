from alpaca_trade_api.stream import Stream
from datetime import datetime
import alpaca_trade_api as tradeapi
import logging

logging.basicConfig(filename="log.txt", level=logging.DEBUG)
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
 
def get_slope():
    return 1.68376483

def on_synch_data(data):
    # access bar data
    spy_data = data["SPY"]
    tlt_data = data["TLT"]
    # save reference of close data for each bar
    spy_close = spy_data.close
    tlt_close = tlt_data.close
    print("spy_close:", spy_close)
    print("tlt_close:", tlt_close)
    
    # calculate spread 
    slope = get_slope()
    print("slope*tlt_close:", slope*tlt_close)
    spread = spy_close - slope*tlt_close
    # we will use the z_score of the spread
    # calculate entry and exit levels for standard deviation
    entry_level = 0.9
    loss_exit_level = 3

    # pass spread and level data to next part for placing trades
    place_trades(spread, entry_level, loss_exit_level)

def place_trades(spread, entry_level, loss_exit_level):
    mean = 205.10297032699404
    std = 14.64338558601404
    slope = get_slope()
    z_score = (spread - mean)/std
	# there is an active position if there is at least 1 position
    active_position = len(alpaca_trade.list_positions()) != 0    
    print("spread", spread)
    print("z score:", z_score)

    #Going short
    if z_score > entry_level and not active_position:
        print("placing short order on TLT")
        alpaca_trade.submit_order(symbol="TLT", qty=slope, type='market', side='buy', time_in_force='day')
        print("placing long order on SPY")
        alpaca_trade.submit_order(symbol="SPY", qty=1, type='market', side='sell', time_in_force='day')

    elif z_score > loss_exit_level and active_position:
        print("liquidating at loss exit level")
        #liquidate if loss exit level is breached
        alpaca_trade.close_all_positions()

    elif z_score < 0.1 and active_position:
        # liquidate if 0 spread is crossed with an active position
        print("closing at 0 spread $$$") 
        alpaca_trade.close_all_positions()
    print(" ")
     
def main():
    alpaca_stream.subscribe_bars(on_equity_bar, "TLT")
    alpaca_stream.subscribe_bars(on_equity_bar, "SPY")

    # start streaming of data
    alpaca_stream.run()

if __name__ == "__main__":
    main()
