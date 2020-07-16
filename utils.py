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

pval_regex = r'((\d+.\d+)|(\d+))(\s{0,1})[*××xX](\s{0,1})10_([−-–]{0,1})(\d+)'

def get_files(base_dir):
    """
    recursively retrieve all PMC.html files from the directory
    
    Args: 
        base_dir: base directory
    
    Return: 
        file_list: a list of filepath
    """
    file_list = []
    files = os.listdir(base_dir)
    for i in files:
        abs_path = os.path.join(base_dir,i)
        if re.match(r'(.*)PMC(.*).html',abs_path):
            file_list.append(abs_path)
        elif os.path.isdir(abs_path)&('ipynb_checkpoints' not in abs_path):
            file_list+=get_files(abs_path)
    return file_list

def process_supsub(soup):
    """
    add underscore (_) before all superscript or subscript text
    
    Args: 
        soup: BeautifulSoup object of html
    
    """
    for sup in soup.find_all(['sup','sub']):
        s = sup.get_text()
        if sup.string==None:
            sup.extract()
        elif re.match('[_-]',s):
            sup.string.replace_with('{} '.format(s))
        else:
            sup.string.replace_with('_{} '.format(s))

def process_em(soup):
    """
    remove all emphasized text
    
    Args: 
        soup: BeautifulSoup object of html

    """
    for em in soup.find_all('em'):
        s = em.get_text()
        if em.string==None:
            em.extract()
        else:
            em.string.replace_with('{} '.format(s))
            

def process_caption(soup):
    """
    remove all caption div tags from html
    
    Args: 
        soup: BeautifulSoup object of html

    """
    for div in soup.find_all('div', attrs='caption'):
        div.extract()

def process_table_figures(soup):
    """
    remove all tables and figures div tags from html
    
    Args: 
        soup: BeautifulSoup object of html

    """
    for div in soup.find_all('div',attrs=['table-wrap','table','fig']):
        div.extract()
        