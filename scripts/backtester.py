### Code based on https://alpaca.markets/learn/google-colab-instant-development-environments/

from alpaca_trade_api.stream import Stream
from datetime import datetime
import alpaca_trade_api as tradeapi
import logging
import backtrader as bt
import matplotlib as mpl

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

spy_bars = alpaca_trade.get_bars('SPY', tradeapi.TimeFrame.Day, '2021-01-01', '2021-03-30').df

def run_backtest(strategy, symbols, start, end, timeframe=tradeapi.TimeFrame.Day, cash=10000):
    '''params:
        strategy: the strategy you wish to backtest, an instance of backtrader.Strategy
        symbols: the symbol (str) or list of symbols List[str] you wish to backtest on
        start: start date of backtest in format 'YYYY-MM-DD'
        end: end date of backtest in format: 'YYYY-MM-DD'
        timeframe: the timeframe the strategy trades on (size of bars) -
                   1 min: TimeFrame.Minute, 1 day: TimeFrame.Day, 5 min: TimeFrame(5, TimeFrameUnit.Minute)
        cash: the starting cash of backtest
    '''

    # initialize backtrader broker
    cerebro = bt.Cerebro(stdstats=True)
    cerebro.broker.setcash(cash)

    # add strategy
    cerebro.addstrategy(strategy)

    # add analytics
    # cerebro.addobserver(bt.observers.Value)
    # cerebro.addobserver(bt.observers.BuySell)
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='mysharpe')
    
    # historical data request
    if type(symbols) == str:
        symbol = symbols
        alpaca_data = alpaca_trade.get_bars(symbol, timeframe, start, end,  adjustment='all').df
        print(alpaca_data)
        data = bt.feeds.PandasData(dataname=alpaca_data, name=symbol)
        cerebro.adddata(data)
    elif type(symbols) == list or type(symbols) == set:
        for symbol in symbols:
            alpaca_data = alpaca_trade.get_bars(symbol, timeframe, start, end, adjustment='all').df
            data = bt.feeds.PandasData(dataname=alpaca_data, name=symbol)
            cerebro.adddata(data)

    # run
    initial_portfolio_value = cerebro.broker.getvalue()
    print(f'Starting Portfolio Value: {initial_portfolio_value}')
    results = cerebro.run()
    final_portfolio_value = cerebro.broker.getvalue()
    print(f'Final Portfolio Value: {final_portfolio_value} ---> Return: {(final_portfolio_value/initial_portfolio_value - 1)*100}%')

    strat = results[0]
    print('Sharpe Ratio:', strat.analyzers.mysharpe.get_analysis()['sharperatio'])
    #cerebro.plot(iplot= False)


class SmaCross(bt.Strategy):
  # list of parameters which are configurable for the strategy
    params = dict(
        pfast=13,  # period for the fast moving average
        pslow=25   # period for the slow moving average
    )

    def __init__(self):
        sma1 = bt.ind.SMA(period=self.p.pfast)  # fast moving average
        sma2 = bt.ind.SMA(period=self.p.pslow)  # slow moving average
        self.crossover = bt.ind.CrossOver(sma1, sma2)  # crossover signal
  
    def next(self):
        if not self.position and self.crossover > 0:  # not in the market
            self.buy()
        elif self.position and self.crossover < 0:  # in the market & cross to the downside
            self.close()  # close long position

class AllWeatherStrategy(bt.Strategy):

    def __init__(self):
        # the last year we rebalanced (initialized to -1)
        self.year_last_rebalanced = -1 
        self.weights = { "VTI" : 0.30 , "TLT" : 0.40, "IEF": 0.15, "GLD" : 0.075, "DBC" : 0.075 }

    def next(self):
        # if we’ve already rebalanced this year
        if self.datetime.date().year == self.year_last_rebalanced:
            return
            
        # update year last balanced
        self.year_last_rebalanced = self.datetime.date().year
        
        # enumerate through each security
        for i,d in enumerate(self.datas):
            # rebalance portfolio with desired target percents
            symbol = d._name
            self.order_target_percent(d, target=self.weights[symbol])

class AllWeatherStrategy(bt.Strategy):

    def __init__(self):
        # the last year we rebalanced (initialized to -1)
        self.year_last_rebalanced = -1 
        self.weights = { "AMT" : 0.30 , "CCL" : 0.40, "FOX": 0.30}

    def next(self):
        # if we’ve already rebalanced this year
        if self.datetime.date().year == self.year_last_rebalanced:
            return
            
        # update year last balanced
        self.year_last_rebalanced = self.datetime.date().year
        
        # enumerate through each security
        for i,d in enumerate(self.datas):
            # rebalance portfolio with desired target percents
            symbol = d._name
            self.order_target_percent(d, target=self.weights[symbol])

run_backtest(AllWeatherStrategy, ["AMT", "CCL", "FOX"] , '2020-01-01', '2020-12-01', tradeapi.TimeFrame.Day, 10000)
#run_backtest(AllWeatherStrategy, ["VTI", "TLT", "IEF", "GLD", "DBC"] , '2015-01-01', '2021-11-01', tradeapi.TimeFrame.Day, 10000)
#run_backtest(SmaCross, 'AAPL', '2019-01-01', '2021-11-01', tradeapi.TimeFrame.Day, 10000)


