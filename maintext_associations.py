import os
import sys
import re
import regex
from itertools import product
import numpy as np
import pandas as pd

import json
import spacy
import pickle
import argparse

def regex_tagger(pattern, label, doc):
    for match in re.finditer(pattern, doc.text):
        char_start, char_end = match.span()
        span = doc.char_span(char_start, char_end)
        if span!=None:
            start,end = span.start,span.end
            new_ent = spacy.tokens.Span(doc,start,end,label=label)
            spans = spacy.util.filter_spans(list(doc.ents)+[new_ent])
            doc.ents = spans

def closest_common_ancester(token_1,token_2):
    """
    assume token_1 closer or equally close to root than token_2
    """
    ancestors = list(token_2.ancestors)
    cur = token_1
    while cur not in ancestors:
        cur = cur.head
    return cur
    
def distance_to_root(sent, token):
    res = 0
    cur = token
    while cur!=sent.root:
        cur = cur.head
        res+=1
    return res

def dp_tree_distance(sent,token_1,token_2):
    dist_1 = distance_to_root(sent,token_1)
    dist_2 = distance_to_root(sent,token_2)

    if dist_2<=dist_1:
        common_ancestor = closest_common_ancester(token_2,token_1)
    else:
        common_ancestor = closest_common_ancester(token_1,token_2)
    dist_3 = distance_to_root(sent,common_ancestor)
    return dist_1+dist_2-2*dist_3
    

if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--pbs_index", type=int, help="pbs index/the file index")
    parser.add_argument("-b", "--base_dir", type=str, help="base directory for html files")
    parser.add_argument("-t", "--target_dir", type=str, help="target directory for spacy output")

    args = parser.parse_args()
    pbs_index = args.pbs_index
    base_dir = args.base_dir
    target_dir = args.target_dir
    
    en_nlp = spacy.load('en')
    file_list = [base_dir+i for i in os.listdir(base_dir)]
    filepath = file_list[pbs_index]

    
    with open(filepath,'rb') as f:
        doc = pickle.load(f)
    regex_tagger(r'(rs)(\d+)', 'SNP', doc)
    with doc.retokenize() as retokenizer:
        for i in doc.ents:
            retokenizer.merge(doc[i.start:i.end])

    associations = []
    for sent in doc.sents:
        snps = [i for i in sent if i.ent_type_=='SNP']
        pvals = [i for i in sent if i.ent_type_=='PVALNUM']
        for pval in pvals:
            min_dist = len(sent)
            associated_snp = None
            for snp in snps:
                distance = dp_tree_distance(sent,snp,pval)
                if distance<=min_dist:
                    min_dist = distance
                    associated_snp = snp
            if associated_snp!=None:
                associations.append([associated_snp,pval])

    pmc = filepath.split('/')[-1].strip('_ner.pkl')

    df = pd.DataFrame(associations,columns=['snp','p-value'])
    df.to_csv(target_dir+'{}_maintext_associations.csv'.format(pmc))

