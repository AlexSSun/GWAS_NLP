#!/usr/bin/env python
# coding: utf-8

import os
import re
from html.parser import HTMLParser
from bs4 import BeautifulSoup
from bs4 import element
from itertools import product
import argparse
import numpy as np
import pandas as pd
import json
from utils import *

def extract_text(soup):
    """
    convert beautiful soup object into a python dict object with cleaned main text body
    
    Args: 
        soup: BeautifulSoup object of html
    
    Return: 
        result: dict of the maintext 
    """
    h1 = soup.find_all('h1',"content-title")[0].get_text()
    main_text = []
#     paragraphs = soup.find_all('p',attrs='p')
    paragraphs =soup.find_all('p',attrs={'id':re.compile('(__|_|)(p|P|Par|par)\d+')})

    for p in paragraphs:
        h2 = p.find_previous('h2','head')
#         h2 = p.parent.find_previous_sibling('h2','head')
        if h2:
            h2=h2.get_text()
        else:
            h2=''
        h3 = p.find_previous_sibling('h3',attrs={'id':re.compile('S[\d]title')})
        if h3:
            h3=h3.get_text()
        else:
            h3=''
        main_text.append([h2,h3,p.get_text()])

    result = {h1:main_text}    
    return result


if __name__=='__main__':
    parser = argparse.ArgumentParser()
    # parser.add_argument("-p", "--pbs_index", type=int, help="pbs index/the file index")
    parser.add_argument("-b", "--base_dir", help="base directory for html files")
    parser.add_argument("-t", "--target_dir", help="target directory for output")

    args = parser.parse_args()
    # pbs_index = args.pbs_index
    base_dir = args.base_dir
    target_dir = args.target_dir

    file_list = get_files(base_dir)
    # filepath = file_list[pbs_index]

    # with open(filepath,'r') as f:
    #         text = f.read()
    # soup = BeautifulSoup(text, 'html.parser')
    # for e in soup.find_all(attrs={'style':['display:none','visibility:hidden']}):
    #     e.extract()
    # # what to do with in sentence reference
    # for ref in soup.find_all(class_=['supplementary-material','figpopup','popnode','bibr']):
    #     ref.extract()

    # process_supsub(soup)
    # process_em(soup)
    # process_caption(soup)
    # process_table_figures(soup)

    # result = extract_text(soup)
    # print(filepath, len(list(result.values())[0]))

    maintext_dict = {}
    for i,filepath in enumerate(file_list):
        
        pmc = filepath.split('/')[-1].strip('.html')
        with open(filepath,'r') as f:
            text = f.read()
        soup = BeautifulSoup(text, 'html.parser')
        for e in soup.find_all(attrs={'style':['display:none','visibility:hidden']}):
            e.extract()
        
        # what to do with in sentence reference
        for ref in soup.find_all(class_=['supplementary-material','figpopup','popnode','bibr']):
            ref.extract()
        process_supsub(soup)
        process_em(soup)
        
        result = extract_text(soup)
        maintext_dict[pmc] = result

    # target_dir = '../output/maintext/'

    for k,v in maintext_dict.items():
        with open(os.path.join(target_dir,"{}_maintext.json".format(k)), "w") as outfile: 
            json.dump(v, outfile) 

