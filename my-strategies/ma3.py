# use MA cross to buy/sell
import datetime
import backtrader as bt
from matplotlib.pyplot import subplot
import pandas as pd
import numpy as np

class MA1Strategy(bt.Strategy):
  params = (
    ('ma_period1', 10),
    ('ma_period2', 60),
  )

  def log(self, txt, dt=None):
    dt = dt or self.datas[0].datetime.date(0)
    print('%s, %s' % (dt.isoformat(), txt))

  def __init__(self):
    self.buy_order = None
    self.sell_order = None

    # Add a MovingAverageSimple indicator
    self.ma1 = bt.indicators.SimpleMovingAverage(self.data, period=self.params.ma_period1)
    self.ma2 = bt.indicators.SimpleMovingAverage(self.data, period=self.params.ma_period2)
    # self.highest = bt.indicators.Highest(self.data, period=self.params.price_period, subplot=False)
    self.isCrossUp = bt.indicators.CrossUp(self.ma1, self.ma2)

    data = pd.read_csv(f'./up_stat_week.csv', index_col='id', dtype={'id': np.character})
    self.stat = {
      'low': data.low['000001'],
      'middle': data.middle['000001'],
      'high': data.high['000001']
    }
    pass

  def notify_order(self, order):
    if order.status in [order.Submitted, order.Accepted]:
      # Buy/Sell order submitted/accepted to/by broker - Nothing to do
      return

    # Check if an order has been completed
    # Attention: broker could reject order if not enough cash
    if order.status in [order.Completed]:
      if order.isbuy():
        # self.log('BUY EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
        #     (order.executed.price,
        #      order.executed.value,
        #      order.executed.comm))

        self.buyprice = order.executed.price
        self.buycomm = order.executed.comm
      else:  # Sell
        pass
        # self.log('SELL EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
        #          (order.executed.price,
        #           order.executed.value,
        #           order.executed.comm))
    elif order.status in [order.Canceled, order.Margin, order.Rejected]:
      self.log('Order Canceled/Margin/Rejected')

  def notify_trade(self, trade):
    if not trade.isclosed:
      return

    self.log('OPERATION PROFIT, GROSS %.2f, NET %.2f' %
             (trade.pnl, trade.pnlcomm))

  def next(self):
    if not self.position:
      if self.check_direction(self.ma2) > 0 and \
        self.is_cross_up() and \
        self.get_percentage(self.data.close[0], self.data.open[0]) >self.stat['middle']:
        # buy 1
        # self.log('BUY CREATE, %.2f, Find high price at: %s, %.2f' % (self.data.close[0], self.data.datetime.date(0 - i).isoformat(), self.data.close[0 - i]))
        self.log('BUY CREATE, %.2f' % (self.data.close[0]))
        self.buy_order = self.buy()
    else:
      if not self.buy_order:
        print('Error.')
        return

      if self.data.close[0] >= self.ma2[0] * (1 + self.stat['high'] * 3 / 100):
        if self.get_percentage(self.data.close[0], self.data.open[0]) > self.stat['high'] \
          or (self.get_percentage(self.data.close[0], self.data.open[0]) > self.stat['middle'] and self.get_percentage(self.data.close[-1], self.data.open[-1]) > self.stat['middle']):
          # sell 1
          self.sell_order = self.sell()
      elif self.is_dead_cross():
        # sell 2
        # self.log('SELL CREATE, %.2f' % close[0])
        self.sell_order = self.sell()

  def check_direction(self, line):
    if line[0] > line[-1]:
      return 1 # up
    elif line[0]  < line[-1]:
      return -1 # down
    else:
      return 0 #

  def is_cross_up(self):
    return self.isCrossUp[0] or self.isCrossUp[-1] or self.isCrossUp[-2]

  def get_percentage(self, val1, val2):
    return (val1 - val2)/val2 * 100

  def is_golden_cross(self):
    return self.ma1[0] >= self.ma2[0] and self.ma1[-1] < self.ma2[-1]

  def is_dead_cross(self):
    return self.ma1[0] < self.ma2[0] and self.ma1[-1] > self.ma2[-1]

  def check_low_price(self):
    close = self.data.close[0]
    i = 0
    while self.data.datetime.date(0 - i) > self.startDate and self.data.close[0 - i] < close * self.params.price_times:
      i = i + 1

    if self.data.datetime.date(0 - i) > self.startDate:
      return True, i
    else:
      return False, 0


if __name__ == '__main__':
  cerebro = bt.Cerebro()
  cerebro.broker.setcash(10000.0)
  cerebro.broker.set_coc(True)
  # cerebro.broker.setcommission(0.0005)
  cerebro.addsizer(bt.sizers.AllInSizer)
  strats = cerebro.addstrategy(MA1Strategy)

  data = bt.feeds.GenericCSVData(
      dataname='./stock_data/0.000001.csv',
      name='000001',
      datetime=1,
      open=2,
      close=3,
      high=4,
      low=5,
      volume=6,
      dtformat=('%Y-%m-%d'),
      fromdate=datetime.datetime(2000, 1, 1),
      todate=datetime.datetime(2020, 1, 1)
  )
  # cerebro.adddata(data)
  # cerebro.resampledata(data, timeframe=bt.TimeFrame.Months)
  cerebro.resampledata(data, timeframe=bt.TimeFrame.Weeks)

  # 策略执行前的资金
  print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())

  cerebro.run()

  # 策略执行后的资金
  print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())

  cerebro.plot(style='candle', barup='red', barupfill=False, bardown='green', plotdist=1, volume=False)