import os
import re

import nltk
import owlready2
import json

def match_phenotype(s,onto):
    a = onto.search_one(label=s,_case_sensitive=False)
    b = onto.search_one(hasBroadSynonym=s,_case_sensitive=False)
    c = onto.search_one(hasRelatedSynonym=s,_case_sensitive=False)
    d = onto.search_one(hasExactSynonym=s,_case_sensitive=False)
    if a or b or c or d:
        result = a or b or c or d
        if result.name.startswith('HP'):
            return result
    return None

def phenotype_recognition(p):
    match = []
    tmp = nltk.tokenize.word_tokenize(p)
    for token_len in range(3,0,-1):
        for i in range(len(tmp)-token_len):
            s = ''
            for j in range(i,i+token_len):
                s+=tmp[j]+' '
            s = s.rstrip()
            if match_phenotype(s,onto):
                match.append(s)
    return match

if __name__=='__main__':
    onto = owlready2.get_ontology("../hp.owl").load()

    filepath = 'PMC5968830_maintext.json'

    with open(filepath,'r') as f:
        text_json = json.load(f)

    title = list(text_json.keys())[0]
    paragraphs = list(text_json.values())[0]
    for paragraph in paragraphs:
        text = paragraph[2]
        sentences = nltk.tokenize.sent_tokenize(text)
        phenotypes_mentioned = []
        for sentence in sentences:
            phenotypes_mentioned+=phenotype_recognition(sentence)
        print(paragraph[0])
        print(phenotypes_mentioned)
        print('-'*80)