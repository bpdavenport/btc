#!/usr/bin/env python

# Usage:
# Download all available CSV files from MtGox account (there should be 4) and 
# cat them together into a single file
#
# Then run btcbasis.py <filename>
#
# Will output a CSV file to STDOUT containing aggregated daily lots, with sales
# being applied in a FIFO manner.

import csv
import sys
import re

class Transaction(object):
    def __init__(self, tid, date):
        self.tid = tid
        self.date = date
        self.btc = None
        self.usd = None
        self.fee = 0

    def handle_entry(self, action, amount):
        if action == 'in':
            self.set_btc(amount)
        elif action == 'out':
            self.set_btc(-amount)
        elif action == 'fee':
            self.set_fee(amount)
        elif action == 'earned':
            self.set_usd(amount)
        elif action == 'spent':
            self.set_usd(-amount)

    def set_btc(self, btc):
        if self.btc is not None:
            raise Error("btc set twice in transaction %s" % self.tid)
        self.btc = btc

    def set_fee(self, fee):
        if self.fee != 0:
            raise Error("fee set twice in transaction %s" % self.tid)
        self.fee = fee

    def set_usd(self, usd):
        if self.usd is not None:
            raise Error("usd set twice in transaction %s" % self.tid)
        self.usd = usd

    def is_complete(self):
        return self.btc is not None and self.usd is not None

    def is_buy(self):
        return self.btc > 0

    def get_net_btc(self):
        if self.is_buy():
            return self.btc - self.fee
        else:
            return -self.btc

    def get_net_usd(self):
        if self.is_buy():
            return -self.usd
        else:
            return self.usd - self.fee

class Lot(object):
    def __init__(self, date, btc, cost):
        self.date = date
        self.btc = btc
        self.cost = cost
        self.sold = False
        self.sale_date = None
        self.sale_proceeds = 0

    def get_price(self):
        return self.cost / self.btc

    def get_sale_price(self):
        return self.sale_proceeds / self.btc

    def get_gain(self):
        return self.sale_proceeds - self.cost

    def sell(self, date, price):
        self.sold = True
        self.sale_date = date
        self.sale_proceeds = self.btc * price

    def split(self, amount):
        lot1 = Lot(self.date, amount, amount / self.btc * self.cost)
        remaining = self.btc - amount
        lot2 = Lot(self.date, remaining, remaining / self.btc * self.cost)
        return (lot1, lot2)

    @classmethod
    def combine(self, lots):
        date = lots[-1].date
        btc = sum(lot.btc for lot in lots)
        cost = sum(lot.cost for lot in lots)
        return Lot(date, btc, cost)

class Aggregator(object):
    def __init__(self):
        self._transactions = dict()
        self._lots = []
        self._sold_lots = []

    def process_file(self, filename):
        with open(filename, 'rb') as csvfile:
            reader = csv.reader(csvfile, delimiter=',', quotechar='"')
            for row in reader:
                try:
                    (date, _) = row[1].split(" ")
                    action = row[2]
                    desc = row[3]
                    amount = float(row[4])
                    m = re.search('tid:([0-9]+)', desc)
                    if m:
                        tid = m.group(1)
                        if tid:
                            if date not in self._transactions:
                                self._transactions[date] = dict()
                            if tid not in self._transactions[date]:
                                self._transactions[date][tid] = Transaction(tid, date)
                            tx = self._transactions[date][tid]
                            tx.handle_entry(action, amount)
                except Exception as e:
                    pass

    def sell_lots(self, date, amount, price):
        remaining = amount
        while remaining > 0:
            lot = self._lots.pop(0)
            if lot.btc > remaining:
                (lot, unsold) = lot.split(remaining)
                self._lots.insert(0, unsold)
            lot.sell(date, price)
            self._sold_lots.append(lot)
            remaining -= lot.btc

    def print_summary(self):
        print "Lot Date,Bought,Price,Cost,Sale Date,Sale Price,Proceeds,Gain"
        for date in sorted(self._transactions.keys()):
            transactions = self._transactions[date]
            buy_btc = 0
            sell_btc = 0
            buy_usd = 0
            sell_usd = 0
            for tx in transactions.values():
                if tx.is_complete():
                    net_btc = tx.get_net_btc()
                    net_usd = tx.get_net_usd()
                    if tx.is_buy():
                        buy_btc += net_btc
                        buy_usd += net_usd
                    else:
                        sell_btc += net_btc
                        sell_usd += net_usd
                else:
                    print "Incomplete tx %s" % tx.tid
            if sell_btc > 0:
                sell_price = sell_usd / sell_btc
                self.sell_lots(date, sell_btc, sell_price)
            if buy_btc > 0:
                lot = Lot(date, buy_btc, buy_usd)
                self._lots.append(lot)

        for lot in self._sold_lots + self._lots:
            if lot.sold:
                print "%s,%s,%s,%s,%s,%s,%s,%s" %  (lot.date,
                                                    lot.btc,
                                                    lot.get_price(),
                                                    lot.cost,
                                                    lot.sale_date,
                                                    lot.get_sale_price(),
                                                    lot.sale_proceeds,
                                                    lot.get_gain())
            else:
                print "%s,%s,%s,%s,,,," % (lot.date,
                                           lot.btc,
                                           lot.get_price(),
                                           lot.cost)

if __name__ == '__main__':
    agg = Aggregator()
    agg.process_file(sys.argv[1])
    agg.print_summary()
