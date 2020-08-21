import os
import sys
import re

# import nltk
import owlready2
import json
import argparse
import pickle

# sys.path.append('../yans_git/abbreviation-extraction/')
from abbreviations import schwartz_hearst
from collections import defaultdict, Counter

import spacy
from spacy.tokens import Span


class Candidate(str):
    def __init__(self, value):
        super().__init__()
        self.start = 0
        self.stop = 0

    def set_position(self, start, stop):
        self.start = start
        self.stop = stop


def yield_lines_from_file(file_path):
    with open(file_path, 'rb') as f:
        for line in f:
            try:
                line = line.decode('utf-8')
            except UnicodeDecodeError:
                line = line.decode('latin-1').encode('utf-8').decode('utf-8')
            line = line.strip()
            yield line


def yield_lines_from_doc(doc_text):
    for line in doc_text.split("."):
        yield line.strip()


def best_candidates(sentence):
    """
    :param sentence: line read from input file
    :return: a Candidate iterator
    """

    if '(' in sentence:
        # Check some things first
        if sentence.count('(') != sentence.count(')'):
            raise ValueError("Unbalanced parentheses: {}".format(sentence))

        if sentence.find('(') > sentence.find(')'):
            raise ValueError("First parentheses is right: {}".format(sentence))

        close_index = -1
        while 1:
            # Look for open parenthesis. Need leading whitespace to avoid matching mathematical and chemical formulae
            open_index = sentence.find(' (', close_index + 1)

            if open_index == -1: break

            # Advance beyond whitespace
            open_index += 1

            # Look for closing parentheses
            close_index = open_index + 1
            open_count = 1
            skip = False
            while open_count:
                try:
                    char = sentence[close_index]
                except IndexError:
                    # We found an opening bracket but no associated closing bracket
                    # Skip the opening bracket
                    skip = True
                    break
                if char == '(':
                    open_count += 1
                elif char in [')', ';', ':']:
                    open_count -= 1
                close_index += 1

            if skip:
                close_index = open_index + 1
                continue

            # Output if conditions are met
            start = open_index + 1
            stop = close_index - 1
            candidate = sentence[start:stop]

            # Take into account whitespace that should be removed
            start = start + len(candidate) - len(candidate.lstrip())
            stop = stop - len(candidate) + len(candidate.rstrip())
            candidate = sentence[start:stop]
            #print (candidate)

            if conditions(candidate):
                new_candidate = Candidate(candidate)
                new_candidate.set_position(start, stop)
                yield new_candidate
            #elif LF_in_parentheses:


def conditions(candidate):
    """
    Based on Schwartz&Hearst

    2 <= len(str) <= 10
    len(tokens) <= 2
    re.search(r'\p{L}', str)
    str[0].isalnum()

    and extra:
    if it matches (\p{L}\.?\s?){2,}
    it is a good candidate.

    :param candidate: candidate abbreviation
    :return: True if this is a good candidate
    """
    LF_in_parentheses=False
    viable = True
    if regex.match(r'(\p{L}\.?\s?){2,}', candidate.lstrip()):
        viable = True
    if len(candidate) < 2 or len(candidate) > 10:
        viable = False
    if len(candidate.split()) > 2:
        viable = False
        LF_in_parentheses=True                #customize funcition find LF in parentheses
    if candidate.islower():                   #customize funcition discard all lower case candidate
        viable = False
    if not regex.search(r'\p{L}', candidate): # \p{L} = All Unicode letter
        viable = False
    if not candidate[0].isalnum():
        viable = False

    return viable


def get_definition(candidate, sentence):
    """
    Takes a candidate and a sentence and returns the definition candidate.

    The definition candidate is the set of tokens (in front of the candidate)
    that starts with a token starting with the first character of the candidate

    :param candidate: candidate abbreviation
    :param sentence: current sentence (single line from input file)
    :return: candidate definition for this abbreviation
    """
    # Take the tokens in front of the candidate
    tokens = regex.split(r'[\s\-]+', sentence[:candidate.start - 2].lower())
    # the char that we are looking for
    key = candidate[0].lower()

    # Count the number of tokens that start with the same character as the candidate
    first_chars = [t[0] for t in filter(None, tokens)]

    definition_freq = first_chars.count(key)
    candidate_freq = candidate.lower().count(key)

    # Look for the list of tokens in front of candidate that
    # have a sufficient number of tokens starting with key
    if candidate_freq <= definition_freq:
        # we should at least have a good number of starts
        count = 0
        start = 0
        start_index = len(first_chars) - 1
        while count < candidate_freq:
            if abs(start) > len(first_chars):
                raise ValueError("candidate {} not found".format(candidate))
            start -= 1
            # Look up key in the definition
            try:
                start_index = first_chars.index(key, len(first_chars) + start)
            except ValueError:
                pass

            # Count the number of keys in definition
            count = first_chars[start_index:].count(key)

        # We found enough keys in the definition so return the definition as a definition candidate
        start = len(' '.join(tokens[:start_index]))
        stop = candidate.start - 1
        candidate = sentence[start:stop]

        # Remove whitespace
        start = start + len(candidate) - len(candidate.lstrip())
        stop = stop - len(candidate) + len(candidate.rstrip())
        candidate = sentence[start:stop]

        new_candidate = Candidate(candidate)
        new_candidate.set_position(start, stop)
        return new_candidate

    else:
        raise ValueError('There are less keys in the tokens in front of candidate than there are in the candidate')


def select_definition(definition, abbrev):
    """
    Takes a definition candidate and an abbreviation candidate
    and returns True if the chars in the abbreviation occur in the definition

    Based on
    A simple algorithm for identifying abbreviation definitions in biomedical texts, Schwartz & Hearst
    :param definition: candidate definition
    :param abbrev: candidate abbreviation
    :return:
    """

    if len(definition) < len(abbrev):
        raise ValueError('Abbreviation is longer than definition')

    if abbrev in definition.split():
        raise ValueError('Abbreviation is full word of definition')

    s_index = -1
    l_index = -1

    while 1:
        try:
            long_char = definition[l_index].lower()
        except IndexError:
            raise

        short_char = abbrev[s_index].lower()

        if not short_char.isalnum():
            s_index -= 1

        if s_index == -1 * len(abbrev):
            if short_char == long_char:
                if l_index == -1 * len(definition) or not definition[l_index - 1].isalnum():
                    break
                else:
                    l_index -= 1
            else:
                l_index -= 1
                if l_index == -1 * (len(definition) + 1):
                    raise ValueError("definition {} was not found in {}".format(abbrev, definition))

        else:
            if short_char == long_char:
                s_index -= 1
                l_index -= 1
            else:
                l_index -= 1

    new_candidate = Candidate(definition[l_index:len(definition)])
    new_candidate.set_position(definition.start, definition.stop)
    definition = new_candidate

    tokens = len(definition.split())
    length = len(abbrev)

    if tokens > min([length + 5, length * 2]):
        raise ValueError("did not meet min(|A|+5, |A|*2) constraint")

    # Do not return definitions that contain unbalanced parentheses
    if definition.count('(') != definition.count(')'):
        raise ValueError("Unbalanced parentheses not allowed in a definition")

    return definition


def extract_abbreviation_definition_pairs(file_path=None,
                                          doc_text=None,
                                          most_common_definition=False,
                                          first_definition=False,
                                          all_definition=False):
    abbrev_map = dict()
    list_abbrev_map = defaultdict(list)
    counter_abbrev_map = dict()
    omit = 0
    written = 0
    if file_path:
        sentence_iterator = enumerate(yield_lines_from_file(file_path))
    elif doc_text:
        sentence_iterator = enumerate(yield_lines_from_doc(doc_text))
    else:
        return abbrev_map

    collect_definitions = False
    if most_common_definition or first_definition or all_definition:
        collect_definitions = True

    for i, sentence in sentence_iterator:
        # Remove any quotes around potential candidate terms
        clean_sentence = regex.sub(r'([(])[\'"\p{Pi}]|[\'"\p{Pf}]([);:])', r'\1\2', sentence)
        try:
            for candidate in best_candidates(clean_sentence):
                try:
                    definition = get_definition(candidate, clean_sentence)
                except (ValueError, IndexError) as e:
                    omit += 1
                else:
                    try:
                        definition = select_definition(definition, candidate)
                    except (ValueError, IndexError) as e:
                        omit += 1
                    else:
                        # Either append the current definition to the list of previous definitions ...
                        if collect_definitions:
                            list_abbrev_map[candidate].append(definition)
                        else:
                            # Or update the abbreviations map with the current definition
                            abbrev_map[candidate] = definition
                        written += 1
        except (ValueError, IndexError) as e:
            print("{} Error processing sentence {}: {}".format(i, sentence, e.args[0]))

    # Return most common definition for each term
    if collect_definitions:
        if most_common_definition:
            # Return the most common definition for each term
            for k,v in list_abbrev_map.items():
                counter_abbrev_map[k] = Counter(v).most_common(1)[0][0]
        elif first_definition:
            # Return the first definition for each term
            for k, v in list_abbrev_map.items():
                counter_abbrev_map[k] = v
        elif all_definition:
            for k, v in list_abbrev_map.items():
                counter_abbrev_map[k] = v
        return counter_abbrev_map

    # Or return the last encountered definition for each term
    return abbrev_map


def match_phenotype(s,onto):
#     s = 'oncology'
    parent_class = onto.search_one(label='Phenotypic abnormality')
    
    a = onto.search_one(label=s,subclass_of=parent_class,_case_sensitive=False)
    b = onto.search_one(hasBroadSynonym=s,subclass_of=parent_class,_case_sensitive=False)
    c = onto.search_one(hasRelatedSynonym=s,subclass_of=parent_class,_case_sensitive=False)
    d = onto.search_one(hasExactSynonym=s,subclass_of=parent_class,_case_sensitive=False)
#     print(a, b , c , d)
    if a or b or c or d:
        result = a or b or c or d
        if result.name.startswith('HP'):
            return result
    return None

def match_pval(s):
    pattern1 = re.compile(r'p(\s|_|-){0,2}value',re.I) # standard pattern
    pattern2 = re.compile(r'p(\s|_|-){0,2}val(\s|$)',re.I) # standard pattern
    pattern3 = re.compile(r'(^|\s)p(_|-|\W|$)') # a single p/P followed by a supscript or no supscript
    pattern4 = re.compile(r'(^|\W|[0-9a-z_-])P([\W_-]|$)')
    flag = pattern1.search(s) or pattern2.search(s) or pattern3.search(s) or pattern4.search(s) 
    if flag:
        return True
    else:
        return False

def match_snp(s):
    pattern1 = re.compile(r'rs(\d){4,8}',re.I) 
    flag = pattern1.search(s)
    if flag:
        return True
    else:
        return False
    
def regex_tagger(pattern, label, doc):
    for match in re.finditer(pattern, doc.text):
        char_start, char_end = match.span()
        span = doc.char_span(char_start, char_end)
        if span!=None:
            start,end = span.start,span.end
            new_ent = spacy.tokens.Span(doc,start,end,label=label)
            spans = spacy.util.filter_spans(list(doc.ents)+[new_ent])
            doc.ents = spans

if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--filepath", type=str, help="filepath of the json file")
    parser.add_argument("-t", "--target_dir", type=str, help="target directory for spacy output")

    args = parser.parse_args()
    filepath = args.filepath
    target_dir = args.target_dir
    pmc = filepath.split('/')[-1].split('_')[0]

    onto = owlready2.get_ontology("/hpo/hp.owl").load()

    with open(filepath,'r') as f:
        text_json = json.load(f)

    title = list(text_json.keys())[0]
    paragraphs = list(text_json.values())[0]


    full_text = [paragraph[2] for paragraph in paragraphs]
    full_text = ''.join(full_text)

    abbre_dict = extract_abbreviation_definition_pairs(doc_text=full_text,most_common_definition=True)
    abbre = list(abbre_dict.keys())

    nlp = spacy.load("en")

    doc = nlp(full_text)
    doc.ents = tuple()

    # phenotype_match,pval_match,snp_match,num_match = keyword_recognition_spacy(doc,abbre)
    hp = []
    for i in onto.classes():
        if i.name.startswith('HP'):
            hp.append(i)

    phenotypes = []
    for i in hp:
        phenotypes+=i.label
        phenotypes+=i.hasExactSynonym
        phenotypes+=i.hasBroadSynonym
        phenotypes+=i.hasRelatedSynonym
    phenotypes = [str(text) for text in phenotypes]

    phrase_matcher = spacy.matcher.PhraseMatcher(nlp.vocab, attr="LOWER")
    phenotypes_pipe = list(nlp.tokenizer.pipe(phenotypes))
    abbre_pipe = list(nlp.tokenizer.pipe(abbre))
    phrase_matcher.add('PHE', None, *phenotypes_pipe)
    phrase_matcher.add('ABBREV', None, *abbre_pipe)

    matches = phrase_matcher(doc)

    entities = []
    for match_id, start, end in matches:
        if doc.vocab.strings[match_id] == "PHE":
            new_ent = Span(doc, start, end, label="PHE")
            entities.append(new_ent)
        elif doc.vocab.strings[match_id] == "ABBREV":
            short = str(doc[start,end])
            long_form = abbre_dict[short]
            if long_form in phenotypes:
                new_ent = Span(doc, start, end, label="PHE")
            else :
                new_ent = Span(doc, start, end, label="ABBREV")
            entities.append(new_ent)

    doc.ents = entities

    regex_tagger(pval_regex, 'PVALNUM', doc)
    regex_tagger(pval_scientific_regex, 'PVALNUM', doc)
    regex_tagger(r'^(rs)(\d+)$', 'SNP', doc)
    
    target_filename = os.path.join(target_dir,pmc+"_ner.pkl")
    with open(target_filename,"wb") as handle:
        pickle.dump(doc,handle)
