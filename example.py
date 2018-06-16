import os
from sympound.sympound import sympound

import time

import platform
distancefun = None
if platform.system() != "Windows":
    from pyxdameraulevenshtein import damerau_levenshtein_distance
    distancefun = damerau_levenshtein_distance
else:
    from jellyfish import levenshtein_distance
    distancefun = levenshtein_distance

def timeit(method):
    def timed(*args, **kw):
        ts = time.time()
        result = method(*args, **kw)
        te = time.time()
        print('%r (%r, %r) %2.2f sec' % (method.__name__, args, kw, te-ts))
        return result
    return timed

ssc = sympound(distancefun=distancefun, maxDictionaryEditDistance=3)

#@profile
@timeit
def test():
    ssc.load_dictionary(os.path.abspath("example-dict1.txt"))
    print(ssc.lookup_compound(input_string="bonjur bonjour", edit_distance_max=2))
    #print(ssc.dictionary.get("bonjour")+"\n")
    print(ssc.lookup_compound(input_string="bonjuor", edit_distance_max=2))
    print()
    print(ssc.load_dictionary("example-dict2.txt", term_index=0, count_index=1))
    print(ssc.lookup_compound(input_string="bonjur hallo", edit_distance_max=2))
    print()

test()