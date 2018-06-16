import os

from sympound import sympound

import platform
distancefun = None
if platform.system() != "Windows":
    from pyxdameraulevenshtein import damerau_levenshtein_distance
    distancefun = damerau_levenshtein_distance
else:
    from jellyfish import levenshtein_distance
    distancefun = levenshtein_distance


ssc = sympound(distancefun=distancefun, maxDictionaryEditDistance=3)

def test():
    ssc.create_dictionary_entry("bonjour", 1)
    print(ssc.lookup_compound(input_string="bonjur bonjour", edit_distance_max=2))
    print()
    print(ssc.lookup_compound(input_string="bonjuor", edit_distance_max=2))
    print()
    print(ssc.load_dictionary("example-dict.txt", term_index=0, count_index=1))
    print(ssc.lookup_compound(input_string="bonjur hallo", edit_distance_max=2))
    print()
    ssc.save_pickle("symspell.pickle")
    #ssc.load_pickle("symspell.pickle")
    print(ssc.lookup_compound(input_string="བཀྲ་ཤས་བད་ལེགས། ལ་མ་", edit_distance_max=3))

test()