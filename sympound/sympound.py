import os
import sys
from copy import copy
import math
import time
import hashlib
import pickle
import gzip
from collections import defaultdict

class SuggestItem(object):
    def __init__(self, term="", distance = 0, count = 0):
        self.term = term
        self.distance = distance
        self.count = count

    def __eq__(self, other):
        """Overrides the default implementation"""
        if isinstance(self, other.__class__):
            return self.term == other.term
        return False

    def __gt__(self, si2):
        """ a simple, default, comparison """
        if self.distance != si2.distance:
            return self.distance > si2.distance
        return self.count < si2.count

    def __str__(self):
        return self.term + ":" + str(self.count) + ":" + str(self.distance)

class sympound(object):
    # initialCapacity and compactLevel are not doing anything at the moment, they're here to mimic the C# constructor
    def __init__(self, distancefun, initialCapacity=16, maxDictionaryEditDistance=2, prefixLength=7, countThreshold=1, compactLevel=5):
        self.distancefun = distancefun
        self.initialCapacity = initialCapacity
        self.maxDictionaryEditDistance = maxDictionaryEditDistance
        self.prefixLength = prefixLength
        self.countThreshold = countThreshold
        self.compactLevel = min(compactLevel, 16)
        # false: assumes input string as single term, no compound splitting / decompounding
        # true:  supports compound splitting / decompounding with three cases:
        # 1. mistakenly inserted space into a correct word led to two incorrect terms
        # 2. mistakenly omitted space between two correct words led to one incorrect combined term
        # 3. multiple independent input terms with/without spelling errors
        self.edit_distance_max = 2
        self.verbose = 0  # //ALLWAYS use verbose = 0 if enableCompoundCheck = true!
        # 0: top suggestion
        # 1: all suggestions of smallest edit distance
        # 2: all suggestions <= editDistanceMax (slower, no early termination)
        # Dictionary that contains both the original words and the deletes derived from them. A term might be both word and delete from another word at the same time.
        # For space reduction a item might be either of type dictionaryItem or Int.
        # A dictionaryItem is used for word, word/delete, and delete with multiple suggestions. Int is used for deletes with a single suggestion (the majority of entries).
        # A Dictionary with fixed value type (int) requires less memory than a Dictionary with variable value type (object)
        # To support two types with a Dictionary with fixed type (int), positive number point to one list of type 1 (string), and negative numbers point to a secondary list of type 2 (dictionaryEntry)
        self.dictionary = {}
        self.deletes = defaultdict(list)
        self.words = {}
        self.belowThresholdWords = {}
        self.max_length = 0

    def create_dictionary_entry(self, key, count):
        if (count <= 0):
            if self.countThreshold > 0:
                return False
            count = 0
        count_previous = -1
        if self.countThreshold > 1 and key in self.belowThresholdWords:
            count = count_previous+count if (sys.maxsize - count_previous > count) else sys.maxsize
            if count >= self.countThreshold:
                self.belowThresholdWords.pop(key)
            else:
                self.belowThresholdWords[key] = count
                return False
        elif key in self.words:
            count = count_previous+count if (sys.maxsize - count_previous > count) else sys.maxsize
            self.words[key] = count
            return False
        elif count < self.countThreshold:
            self.belowThresholdWords[key] = count
            return False
        self.words[key] = count
        if len(key) > self.max_length:
            self.max_length = len(key)
        edits = self.edits_prefix(key)
        for delete in edits:
            deleteHash = self.get_string_hash(delete)
            self.deletes[deleteHash].append(key)
        return True

    def get_string_hash(self, s):
        return hashlib.md5(s.encode('utf-8')).hexdigest()

    def save_pickle(self, filename, compressed=True):
        pickle_data = {"deletes": self.deletes, "words": self.words, "max_length": self.max_length}
        with (gzip.open if compressed else open)(filename, "wb") as f:
            pickle.dump(pickle_data, f)

    def load_pickle(self, filename, compressed=True):
        with (gzip.open if compressed else open)(filename, "rb") as f:
            pickle_data = pickle.load(f)
        self.deletes = pickle_data["deletes"]
        self.words = pickle_data["words"]
        self.max_length = pickle_data["max_length"]
        return True

    def delete_in_suggestion_prefix(self, delete, delete_len, suggestion, suggestion_len):
        if delete_len == 0:
            return True
        if self.prefixLength < suggestion_len:
            suggestion_len = self.prefixLength
        j = 0
        for c in delete:
            while j < suggestion_len and c != suggestion[j]:
                j += 1
            if j == suggestion_len:
                return False
        return True

    def load_dictionary(self, filepath=None, dict_tokens=None, term_index=0, count_index=1):
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                tokens = line.split()
                if len(tokens) >= 2:
                    key = tokens[term_index]
                    count = int(tokens[count_index])
                    self.create_dictionary_entry(key=key, count=count)
        self.belowThresholdWords = {}
        return True

    def add_lowest_distance(self, item, suggestion, suggestion_int, delete):
        if self.verbose < 2 and len(item.suggestions) > 0 and (
                len(self.word_list[item.suggestions[0]]) - len(delete)) > (len(suggestion) - len(delete)):
            item.suggestions.clear()

        if self.verbose == 2 or len(item.suggestions) == 0 or (
                    len(self.word_list[item.suggestions[0]]) - len(delete) >= len(suggestion) - len(delete)):
            item.suggestions.append(suggestion_int)
        return item

    def edits_prefix(self, key):
        hashSet = []
        keylen = len(key)
        if keylen <= self.maxDictionaryEditDistance:
            hashSet.append("")
        if keylen > self.prefixLength:
            key = key[:self.prefixLength]
        hashSet.append(key)
        return self.edits(key, 0, hashSet)

    def edits(self, word, edit_distance, deletes):
        edit_distance += 1
        wordlen = len(word)
        if wordlen > 1:
            for index in range(0, wordlen):
                delete = word[:index] + word[index + 1:]
                if delete not in deletes:
                    deletes.append(delete)
                    if edit_distance < self.maxDictionaryEditDistance:
                        self.edits(delete, edit_distance, deletes)
        return deletes

    def lookup(self, input_string, verbosity, edit_distance_max):
        if edit_distance_max > self.maxDictionaryEditDistance:
            return []
        input_len = len(input_string)
        if (input_len - edit_distance_max) > self.max_length:
            return []

        suggestions = [] # list of SuggestItems
        hashset1 = set()
        hashset2 = set()

        if input_string in self.words:
            suggestions.append(SuggestItem(input_string, 0, self.words[input_string]))

        hashset2.add(input_string)

        edit_distance_max2 = edit_distance_max
        candidates_index = 0
        singleSuggestion = [""]
        candidates = [] # list of strings

        input_prefix_len = input_len
        if input_prefix_len > self.prefixLength:
            input_prefix_len = self.prefixLength
            candidates.append(input_string[:input_prefix_len])
        else:
            candidates.append(input_string)
        while candidates_index < len(candidates):
            candidate = candidates[candidates_index]
            candidates_index+=1
            candidate_len = len(candidate)
            lengthDiff = input_prefix_len - candidate_len

            if lengthDiff > edit_distance_max2:
                if verbosity == 2:
                    continue
                break
            candidateHash = self.get_string_hash(candidate)
            if candidateHash in self.deletes:
                dict_suggestions = self.deletes[candidateHash]
                for suggestion in dict_suggestions:
                    if suggestion == input_string:
                        continue
                    suggestion_len = len(suggestion)
                    if (abs(suggestion_len - input_len) > edit_distance_max2 or
                        suggestion_len < candidate_len or
                        (suggestion_len == candidate_len and suggestion != candidate)):
                        continue
                    sugg_prefix_len = min(suggestion_len, self.prefixLength)
                    if sugg_prefix_len > input_prefix_len and (sugg_prefix_len - candidate_len) > edit_distance_max2:
                        continue
                    distance = 0
                    if candidate_len == 0:
                        distance = min(input_len, suggestion_len)
                        if distance > edit_distance_max2:
                            continue
                        if suggestion in hashset2:
                            continue
                        hashset2.add(suggestion)
                    elif suggestion_len == 1:
                        if input_string.find(suggestion[0]) < 0:
                            distance = input_len
                        else:
                            distance = input_len -1
                        if distance > edit_distance_max2:
                            continue
                        if suggestion in hashset2:
                            continue
                        hashset2.add(suggestion)
                    else:
                        len_min = min(input_len, suggestion_len) - self.prefixLength
                        if ((self.prefixLength - edit_distance_max == candidate_len and
                            len_min > 1 and input_string[input_len+1-len_min:] != suggestion[suggestion_len+1-len_min:]) or
                            (len_min > 0 and input_string[input_len-len_min] != suggestion[suggestion_len-len_min] and
                            (input_string[input_len-len_min-1] != suggestion[suggestion_len-len_min] or input_string[input_len-len_min] != suggestion[suggestion_len-len_min-1]))):
                            continue
                        else:
                            if verbosity < 2 and not self.delete_in_suggestion_prefix(candidate, candidate_len, suggestion, suggestion_len) or suggestion in hashset2:
                                continue
                            if suggestion not in hashset2:
                                hashset2.add(suggestion)
                            distance = self.distancefun(input_string, suggestion)
                            if distance < 0:
                                continue
                    if distance <= edit_distance_max2:
                        suggestion_count = self.words[suggestion]
                        si = SuggestItem(suggestion, distance, suggestion_count)
                        if len(suggestions) > 0:
                            if verbosity == 1:
                                if distance < edit_distance_max2:
                                    suggestions = []
                                break
                            elif verbosity == 0:
                                if distance < edit_distance_max2 or suggestion_count > suggestions[0].count:
                                    edit_distance_max2 = distance
                                    suggestions[0] = si
                                continue
                        if verbosity < 2:
                            edit_distance_max2 = distance
                        suggestions.append(si)

            if lengthDiff < edit_distance_max and candidate_len <= self.prefixLength:
                if verbosity < 2 and lengthDiff > edit_distance_max2:
                    continue
                for index in range(0, candidate_len):
                    delete = candidate[:index] + candidate[index + 1:]
                    if delete not in hashset1:
                        candidates.append(delete)
                    else:
                        hashset1.add(delete)
        if len(suggestions) > 1:
            suggestions = sorted(suggestions)
        return suggestions

    def lookup_compound(self, input_string, edit_distance_max):
        term_list_1 = input_string.split()
        suggestions = []
        suggestion_parts = []

        last_combi = False

        for i in range(len(term_list_1)):
            suggestions_previous_term = [copy(suggestion) for suggestion in suggestions]
            suggestions = self.lookup(term_list_1[i], 0, edit_distance_max)
            if i > 0 and not last_combi:
                suggestions_combi = self.lookup(term_list_1[i-1] + term_list_1[i], 0, edit_distance_max)
                if len(suggestions_combi) > 0:
                    best1 = suggestion_parts[-1]
                    best2 = None
                    if len(suggestions) > 0:
                        best2 = suggestions[0]
                    else:
                        best2 = SuggestItem(term_list_1[i], edit_distance_max+1, 0)
                    distance1 = self.distancefun(term_list_1[i-1]+" "+term_list_1[i], best1.term+" "+best2.term)
                    if distance1 > 0 and suggestions_combi[0].distance + 1 < distance1:
                        suggestions_combi[0].distance += 1
                        suggestion_parts[-1] = suggestions_combi[0]
                        last_combi = True
                        break
            last_combi = False

            if len(suggestions) > 0 and (suggestions[0].distance == 0 or len(term_list_1[i]) == 1):
                suggestion_parts.append(suggestions[0])
            else:
                suggestions_split = []
                if len(suggestions) > 0:  # 473
                    suggestions_split.append(suggestions[0])
                if len(term_list_1[i]) > 1:
                    for j in range(1, len(term_list_1[i])):
                        part1 = term_list_1[i][0:j]
                        part2 = term_list_1[i][j:]
                        suggestion_split = SuggestItem()
                        suggestions1 = self.lookup(part1, 0, edit_distance_max)
                        if len(suggestions1) > 0:
                            if len(suggestions) > 0 and suggestions[0].term == suggestions1[0].term:
                                break
                            suggestions2 = self.lookup(part2, 0, edit_distance_max)
                            if len(suggestions2) > 0:
                                # if split correction1 == einzelwort correction
                                if len(suggestions) > 0 and suggestions[0].term == suggestions2[0].term:
                                    break
                                suggestion_split.term = suggestions1[0].term + " " + suggestions2[0].term
                                distance2 = self.distancefun(term_list_1[i], suggestions1[0].term+" "+suggestions2[0].term)
                                if distance2 < 0:
                                    distance2 = edit_distance_max+1
                                suggestion_split.distance = distance2
                                suggestion_split.count = min(suggestions1[0].count, suggestions2[0].count)
                                suggestions_split.append(suggestion_split)
                                if suggestion_split.distance == 1:
                                    break
                    if len(suggestions_split) > 0:
                        suggestions_split = sorted(suggestions_split, key=lambda x: 2 * x.distance - x.count, reverse=False)
                        suggestion_parts.append(suggestions_split[0])
                    else:
                        si = SuggestItem(term_list_1[i], edit_distance_max+1, 0)
                        suggestion_parts.append(si)
                else:
                    si = SuggestItem(term_list_1[i], edit_distance_max+1, 0)
                    suggestion_parts.append(si)
        suggestion = SuggestItem()
        suggestion.count = math.inf
        s = ""
        for si in suggestion_parts:
            s += si.term + " "
            suggestion.count = min(si.count, suggestion.count)
        suggestion.term = s.strip()
        suggestion.distance = self.distancefun(suggestion.term, input_string)
        return suggestion
