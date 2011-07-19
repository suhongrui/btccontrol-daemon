#!/usr/bin/python2.7
import os,re,math,sys,time
import urllib2,json
import functools

class OneTime(object):
    def __init__(self,name='Timer'):
        self.name = name
        self.start = time.time()
    def __del__(self):
        print '{0}: {1:.2f}s'.format(self.name,time.time()-self.start)

class memoize(object): 
    def __init__(self, func): 
        self.func = func 
        self.memoized = {} 
        self.method_cache = {} 
    def __call__(self, *args): 
        return self.cache_get(self.memoized, args, 
            lambda: self.func(*args)) 
    def __get__(self, obj, objtype): 
        return self.cache_get(self.method_cache, obj, 
            lambda: self.__class__(functools.partial(self.func, obj))) 
    def cache_get(self, cache, key, func): 
        try: 
            return cache[key] 
        except KeyError: 
            cache[key] = func() 
            return cache[key] 
      
try:
    import memcache
    _memcached = memcache.Client(['{0}:{1}'.format('localhost',11211)], debug=0)
    if not _memcached.set('junk',1):
        raise Exception("Memcached not running.")
except:
    def cacheoize(key,timeout=30): # Can't get memcache? Just memoize...
        return memoize
else:
    def cacheoize(key,timeout=30):
        def _cacheoize(function):
            def func(*args):
                mckey = 'bcenv.{0}.{1}'.format(key,'.'.join([str(a) for a in args]))
                val = _memcached.get(key)
                if val is None:
                    val = function(*args)
                    _memcached.set(key,val,timeout)
                return val
            return func
        return _cacheoize

@memoize
class BitcoinStats(object):
    @memoize
    def be(self):
        class BE(object):
            def __getattr__(self,func):
                def __function(*args):
                    url = 'http://blockexplorer.com/q/{0}/{1}'.format(func,'/'.join([str(a) for a in args]))
                    return urllib2.urlopen(url).read().strip()
                return __function
        return BE()
    
    @cacheoize('difficulty',360)
    def getDifficulty(self): 
        try: return float(self.be().getdifficulty())
        except urllib2.URLError:
            return float(urllib2.urlopen('http://www.alloscomp.com/bitcoin/difficulty.php').read().strip())
    
    @cacheoize('nextdifficulty',360)
    def getNextDifficulty(self): return float(self.be().estimate())
    
    @cacheoize('target',360)
    def getTarget(self): return int(self.be().decimaltarget())
    
    @cacheoize('blockCount',30)
    def getBlockCount(self): 
        try: return int(self.be().getblockcount())
        except urllib2.URLError:
            return int(urllib2.urlopen('http://www.alloscomp.com/bitcoin/blockCount.php').read().strip())
    
    @cacheoize('bitcoinsPerBlock',3600)
    def getBitcoinsPerBlock(self): 
        try: return float(self.be().bcperblock())
        except urllib2.URLError:
            return 50.0
    
    @cacheoize('lastMtGox',10)
    def getLastMtGox(self): 
        return 0.0 # MtGox is down :(
        retry = 0
        RETRIES = 5
        while 1:
            try:
                return float(json.loads(urllib2.urlopen('https://mtgox.com/code/data/ticker.php').read())['ticker']['last'])
            except:
                retry += 1
                if retry > RETRIES:
                    return 0.0
                time.sleep(1)
            else:
                break

def getTimePerBlock(difficulty,hashrate):
    target = 0x00000000ffff0000000000000000000000000000000000000000000000000000 / difficulty
    return math.pow(2,256)/(target*hashrate)    
    
def getHumanHashRate(hashrate):
    suffix = ['','K','M','G','T','P']
    humanhashrate = hashrate
    factor = 0
    while humanhashrate > 1000 and factor < len(suffix):
        humanhashrate /= 1000.0
        factor += 1
    return "{0:.2f}{1}".format(humanhashrate,suffix[factor])
def getHumanTime(time):
    humanTimePerBlock = time
    TIME = [('min',60), ('hrs',60), ('days',24)]
    fsuffix = 'sec'
    for suffix,interval in TIME:
        if humanTimePerBlock > interval:
            humanTimePerBlock /= interval
            fsuffix = suffix
        else: break
    return "{0:.1f} {1}".format(humanTimePerBlock,fsuffix)

class VariousTimeScales(object):
    def __init__(self,second):
        self.second = second    
    @property
    def minute(self): return self.second * 60
    @property
    def hour(self): return self.second * 3600
    @property
    def day(self): return self.second * 3600 * 24
    @property
    def week(self): return self.second * 3600 * 24 * 7 # Fixed a dumb mistake (thanks Andy!)
    @property
    def month(self): return self.second * 3600 * 24 * 30.4
    @property
    def year(self): return self.second * 3600 * 24 * 365.25
    def __mul__(self,other): return VariousTimeScales(self.second*other)
    def __div__(self,other): return VariousTimeScales(self.second/other)
    def __str__(self):
        return 'Per-Second: {0.second}\nPer-Hour: {0.hour}\nPer-Day: {0.day}\nPer-Week: {0.week}\nPer-Month: {0.month}\nPer-Year: {0.year}'.format(self)
    
def calculate(hashrate,difficulty=None,exchange_rate=None):
    bs = BitcoinStats()
    if difficulty is None: difficulty = bs.getDifficulty()
    if exchange_rate is None: exchange_rate = bs.getLastMtGox()
    
    time_per_block = getTimePerBlock(difficulty,hashrate)
    coins = VariousTimeScales(bs.getBitcoinsPerBlock() / time_per_block)
    dollars = coins * exchange_rate
    
    return time_per_block,coins,dollars

if __name__ == '__main__':        
    if len(sys.argv) < 2:
        sys.exit("Error: first argument must be hash rate in khps.")
    hashrate = int(sys.argv[1]) * 1000
    difficulty = int(sys.argv[2]) if len(sys.argv) >= 3 else None

    time_per_block,coins,dollars = calculate(hashrate,difficulty)

    print "Hash rate:    {0} hash/sec".format(getHumanHashRate(hashrate))
    print "Difficulty:   {0:.1f}".format(BitcoinStats().getDifficulty())
    print "Value:        ${0:.3f}/BTC".format(BitcoinStats().getLastMtGox())
    print "Time/block:   {0}".format(getHumanTime(time_per_block))
    print u"BTC/Day: \u0E3F{0:7.2f}\t$/Day: ${1:8.2f}".format(coins.day,dollars.day)
    print u"BTC/Wk.: \u0E3F{0:7.2f}\t$/Wk.: ${1:8.2f}".format(coins.week,dollars.week)
    print u"BTC/Mo.: \u0E3F{0:7.2f}\t$/Mo.: ${1:8.2f}".format(coins.month,dollars.month)
    print u"BTC/Mo.: \u0E3F{0:7.2f}\t$/Mo.: ${1:8.2f}".format(coins.year,dollars.year)
