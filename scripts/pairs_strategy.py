from alpaca_trade_api.stream import Stream
from datetime import datetime
import alpaca_trade_api as tradeapi

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
 
async def on_crypto_bar(bar):
    if bar.exchange != 'CBSE':
        return
    # bar data passed to intermediary function
    synch_datafeed(bar)

def get_slope():
    return 70

def on_synch_data(data):
    # access bar data
    btc_data = data["BTCUSD"]
    coin_data = data["COIN"]
    # save reference of close data for each bar
    btc_close = btc_data.close
    coin_close = coin_data.close
    print("btc_close:", btc_close)
    print("coin_close:", coin_close)
    
    # calculate spread 
    slope = get_slope()
    print("slope*coin_close:", slope*coin_close)
    spread = btc_close - slope*coin_close
    # we will use the z_score of the spread
    # calculate entry and exit levels for standard deviation
    entry_level = 1
    loss_exit_level = 2

    # pass spread and level data to next part for placing trades
    place_trades(spread, entry_level, loss_exit_level)

def place_trades(spread, entry_level, loss_exit_level):
    mean = 17113.171963557063
    std = 2819.025038118409
    slope = get_slope()
    z_score = (spread - mean)/std
	# there is an active position if there is at least 1 position
    active_position = len(alpaca_trade.list_positions()) != 0    
    print("spread", spread)
    print("z score:", z_score)
    
    #Going short on the spread?
    if z_score < -entry_level and not active_position:
        print("placing short order on COIN")
        alpaca_trade.submit_order(symbol="COIN", qty=slope, type='market', side='sell', time_in_force='day')
        print("placing long order on BTC")
        alpaca_trade.submit_order(symbol="BTCUSD", qty=1, type='market', side='buy', time_in_force='gtc')

    elif z_score < -loss_exit_level and active_position:
        print("liquidating at loss exit level")
        #liquidate if loss exit level is breached
        alpaca_trade.close_all_positions()

    elif z_score > 0 and active_position and not position_long:
        # liquidate if 0 spread is crossed with an active position
        print("closing at 0 spread $$$") 
        alpaca_trade.close_all_positions()
    print(" ")
 

def main():
    # subscribe to coinbase stock data and assign handler
    alpaca_stream.subscribe_bars(on_equity_bar, "COIN")

    # subscribe to Bitcoin data and assign handler
    alpaca_stream.subscribe_crypto_bars(on_crypto_bar, "BTCUSD")

    # start streaming of data
    alpaca_stream.run()

if __name__ == "__main__":
    main()
