import os
import re

import nltk
import owlready2
import json

def match_phenotype(s,onto):
    """
    identify if the query string is a phenotype using ontology
    
    Args: 
        s: query string 
        onto: ontology object
    
    Return: 
        result: ontology class
    """
    parent_class = onto.search_one(label='Phenotypic abnormality')
    
    label = onto.search_one(label=s,subclass_of=parent_class,_case_sensitive=False)
    broad_syn = onto.search_one(hasBroadSynonym=s,subclass_of=parent_class,_case_sensitive=False)
    related_syn = onto.search_one(hasRelatedSynonym=s,subclass_of=parent_class,_case_sensitive=False)
    exact_syn = onto.search_one(hasExactSynonym=s,subclass_of=parent_class,_case_sensitive=False)

    if label or broad_syn or related_syn or exact_syn:
        result = label or broad_syn or related_syn or exact_syn
        if result.name.startswith('HP'):
            return result
    return None

def match_pval(s):
    """
    identify if the query string means "p value" using regex
    
    Args: 
        s: query string 
    
    Return: 
        result: bool
    """
    pattern1 = re.compile(r'p(\s|_|-){0,1}value',re.I) # standard pattern
    pattern2 = re.compile(r'p(\s|_|-){0,1}val(\s|$)',re.I) # standard pattern
    pattern3 = re.compile(r'(^|\s)p(_|-|\W|$)') # a single p/P followed by a supscript or no supscript
    pattern4 = re.compile(r'(^|\W|[0-9a-z_-])P([\W_-]|$)')
    flag = pattern1.search(s) or pattern2.search(s) or pattern3.search(s) or pattern4.search(s) 
    if flag:
        return True
    else:
        return False

def match_snp(s):
    """
    identify if the query string is a snp by looking for rs number
    
    Args: 
        s: query string 
    
    Return: 
        result: bool
    """
    pattern1 = re.compile(r'rs(\d){4,8}',re.I) 
    flag = pattern1.search(s)
    if flag:
        return True
    else:
        return False

def keyword_recognition(p):
    """
    find all keywords in a paragraph of text
    
    Args: 
        p: string paragraph
    
    Return: 
        phenotype_match: matched phenotypes
        pval_match: matched pvals
        snp_match: matched snps
    """
#     loc = []
    phenotype_match = []
    pval_match = []
    snp_match = []
    tmp = nltk.tokenize.word_tokenize(p)
    for token_len in range(3,0,-1):
        for i in range(len(tmp)-token_len):
            s = ''
            for j in range(i,i+token_len):
                s+=tmp[j]+' '
            s = s.rstrip()
            # if ',.()' in s, then skip
            if re.findall(r"\W",s):
                continue
            if match_phenotype(s,onto):
                phenotype_match.append(s)
            elif match_pval(s) and token_len<=1:
                pval_match.append(s)
            elif match_snp(s) and token_len==1:
                snp_match.append(s)
    return phenotype_match,pval_match,snp_match

if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--filepath", type=int, help="filepath of the json file")

    args = parser.parse_args()
    filepath = args.filepath

    # filepath = 'PMC5968830_maintext.json'
    
    onto = owlready2.get_ontology("../hp.owl").load()

    with open(filepath,'r') as f:
        text_json = json.load(f)

    title = list(text_json.keys())[0]
    paragraphs = list(text_json.values())[0]

    for paragraph in paragraphs:
        header = paragraph[0]
        if header.lower() not in ['abstract','methods','results','discussion']:
            continue
        text = paragraph[2]
        sentences = nltk.tokenize.sent_tokenize(text)
        phenotype_match,pval_match,snp_match = [],[],[]
        for sentence in sentences:
            tmp_phenotype_match,tmp_pval_match,tmp_snp_match=keyword_recognition(sentence)
            phenotype_match += tmp_phenotype_match
            pval_match += tmp_pval_match
            snp_match += tmp_snp_match
        print('section: ', paragraph[0])
        print('phenotypes: ', phenotype_match)
        print('pval: ', pval_match)
        print('snp: ', snp_match)
        print('-'*80)