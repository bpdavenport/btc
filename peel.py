#!/usr/bin/env python

import sys
import json
import urllib2
import time
import re

API_BASE = "https://blockchain.info"

def get_tx(txid):
    if len(str(txid)) > 20:
        url = "%s/rawtx/%s" % (API_BASE, txid)
    else:
        url = "%s/tx-index/%s?format=json" % (API_BASE, txid)
    tx = json.load(urllib2.urlopen(url))
    return tx

def get_address(addr):
    url = "%s/rawaddr/%s" % (API_BASE, addr)
    return json.load(urllib2.urlopen(url))

def largest_output(tx):
    out = tx['out']
    largest = 0
    sum = 0
    largest_output = None
    for output in out:
        value = output['value']
        sum += value
        if value > largest:
            largest = value
            largest_output = output
    if largest < 10000000000:
        return None
    return largest_output

def outgoing_tx(addrinfo):
    if addrinfo['n_tx'] != 2:
        return None
    for tx in addrinfo['txs']:
        if tx['result'] == 0:
            return tx
    return None

def follow_peel(txid=None, addr=None):
    tx = None
    if txid:
        tx = get_tx(txid)
    elif addr:
        addrinfo = get_address(addr)
        if not addrinfo:
            return
        tx = outgoing_tx(addrinfo)
    if not tx:
        return
    output = largest_output(tx)
    if not output:
        return
    t = tx['time']
    print "%s\t%s\t%10d\t%s\t%s" % (t, time.asctime(time.gmtime(t)), output['value'] / 1e8, output['tx_index'], output['addr'])
    follow_peel(None, output['addr'])

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print "Usage: peel.py <txhash | txindex | address>"
        sys.exit(0)
    id = sys.argv[1]
    if re.search("[G-Zg-z]", id):
        # address
        follow_peel(None, id)
    else:
        follow_peel(id)
