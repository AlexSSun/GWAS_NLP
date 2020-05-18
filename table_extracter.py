#!/usr/bin/env python
# coding: utf-8

# In[1]:


from IPython import display

import os
import re
from html.parser import HTMLParser
from bs4 import BeautifulSoup
from bs4 import element
from itertools import product
import numpy as np
import pandas as pd
import argparse
import nltk
import json

parser = argparse.ArgumentParser()
parser.add_argument("-p", "--pbs_index", type=int, help="pbs index/the file index")
parser.add_argument("-t", "--target_dir", help="target directory for output")

args = parser.parse_args()
pbs_index = args.pbs_index
target_dir = args.target_dir


# # Superscripts and subscripts

# In[2]:


def process_supsub(soup):
    for sup in soup.find_all(['sup','sub']):
        s = sup.get_text()
        if sup.string==None:
            sup.extract()
        elif re.match('[_-]',s):
            sup.string.replace_with('{} '.format(s))
        else:
            sup.string.replace_with('_{} '.format(s))

def process_em(soup):
    for em in soup.find_all('em'):
        s = em.get_text()
        if em.string==None:
            em.extract()
        else:
            em.string.replace_with('{} '.format(s))
            


# # Get file paths

# In[3]:


def get_files(base_dir):
    file_list = []
    files = os.listdir(base_dir)
    for i in files:
        abs_path = os.path.join(base_dir,i)
        if re.match(r'(.*)PMC(.*).html',abs_path):
            file_list.append(abs_path)
        elif os.path.isdir(abs_path)&('ipynb_checkpoints' not in abs_path):
            file_list+=get_files(abs_path)
    return file_list


# base_dir = '../NLP-GWAS/'
base_dir = '../NLP-GWAS/Dev Set/'

file_list = get_files(base_dir)


# # Load Soup

# In[51]:

filepath = file_list[pbs_index]
pmc = filepath.split('/')[-1].strip('.html')


with open(filepath,'r') as f:
        text = f.read()
soup = BeautifulSoup(text, 'html.parser')


# # Preprocssing

# In[52]:


for e in soup.find_all(attrs={'style':['display:none','visibility:hidden']}):
    e.extract()

# what to do with in sentence reference
for ref in soup.find_all(class_=['supplementary-material','figpopup','popnode','bibr']):
    ref.extract()

process_supsub(soup)
process_em(soup)


# # One table

# In[53]:


for table in soup.find_all('table',recursive=True):


    # ## caption and footer

    # In[54]:


    caption = table.find_previous('div','caption').get_text()


    # In[59]:


    footer = [i.get_text() for i in table.parent.find_next_siblings('div','tblwrap-foot')]


    # In[60]:


    caption


    # In[61]:


    footer


    # ## find header rows

    # In[64]:


    header_idx = []
    for idx,row in enumerate(table.findAll('tr')):
        if row.findAll('th'):
            header_idx.append(idx)


    # ## span table to single-cells

    # In[189]:


    def table_to_2d(t):
        # https://stackoverflow.com/questions/48393253/how-to-parse-table-with-rowspan-and-colspan
        
        rows = t.find_all('tr')

        # first scan, see how many columns we need
        n_cols = sum([int(i.attrs['colspan']) for i in t.find('tr').findAll(['th','td'])])
        
        # build an empty matrix for all possible cells
        table = [[None] * n_cols for row in rows]

        # fill matrix from row data
        rowspans = {}  # track pending rowspans, column number mapping to count
        for row_idx, row in enumerate(rows):
            span_offset = 0  # how many columns are skipped due to row and colspans 
            for col_idx, cell in enumerate(row.findAll(['td', 'th'])):
                # adjust for preceding row and colspans
                col_idx += span_offset
                while rowspans.get(col_idx, 0):
                    span_offset += 1
                    col_idx += 1

                # fill table data
    #             rowspan = rowspans[col_idx] = int(cell.attrs['rowspan']) or len(rows) - row_idx
    #             colspan = int(cell.attrs['colspan']) or n_cols - col_idx
                rowspan = rowspans[col_idx] = int(cell.attrs['rowspan'])
                colspan = int(cell.attrs['colspan'])
                # next column is offset by the colspan
                span_offset += colspan - 1
                value = cell.get_text()
                for drow, dcol in product(range(rowspan), range(colspan)):
                    try:
                        table[row_idx + drow][col_idx + dcol] = value
                        rowspans[col_idx + dcol] = rowspan
                    except IndexError:
                        # rowspan or colspan outside the confines of the table
                        pass
            # update rowspan bookkeeping
            rowspans = {c: s - 1 for c, s in rowspans.items() if s > 1}
        return table


    # In[204]:


    table_2d = table_to_2d(table)


    # ## find superrows

    # In[174]:


    def check_superrow(row):
        if len(set([i for i in row if (str(i)!='')&(str(i)!='\n')&(str(i)!='None')]))==1:
            return True
        else:
            return False


    # In[175]:


    superrow_idx = []
    if table_2d!=None:
        for row_idx,row in enumerate(table_2d):
            if row_idx not in header_idx:
                if check_superrow(row):
                    superrow_idx.append(row_idx)


    # In[176]:


    [table_2d[i] for i in superrow_idx]


    # ## split pattern

    # In[205]:
 

    def find_format(header):
    #     parts = nltk.tokenize.word_tokenize(header)
        a = re.split(r'[:|/,;]', header)
        b = re.findall(r'[:|/,;]', header)
        parts = []
        for i in range(len(b)):
            parts+=[a[i],b[i]]
        parts.append(a[-1])
        parts
        
        # identify special character
        special_char_idx = []
        for idx,part in enumerate(parts):
            if part in ':|\/,;':
                special_char_idx.append(idx)
        
        # generate regex pattern
        if special_char_idx:
            pattern = r''
            for idx in range(len(parts)):
                if idx in special_char_idx:
                    char = parts[idx]
                    pattern+='({})'.format(char)
                else:
                    pattern+='(\w+)'
            pattern = re.compile(pattern)
            return pattern
        else:
            return None

    def test_format(pattern,s):
        if re.search(pattern,s):
            return True
        return False

    def split_format(pattern,s):
    #     return pattern.split(s)[1:-1]
    #     return [i for i in pattern.split(s) if i not in ':|\/,;']
        return [i for i in re.split(r'[:|/,;]', s) if i not in ':|\/,;']


    # In[206]:


    for col_idx,th in enumerate(table_2d[header_idx[-1]]):

        print("\rProgress {:2.1%}".format(col_idx / len(table_2d[header_idx[-1]])))
        display.clear_output(wait=True)
        
        pattern = find_format(th)
        if pattern:
            cnt = 0
            for row_idx in range(len(table_2d)):
                if (row_idx not in header_idx)&(row_idx not in superrow_idx):
                    cnt+=test_format(pattern,table_2d[row_idx][col_idx])
            # if all elements follow the same pattern
            if cnt==len(table_2d)-len(header_idx)-len(superrow_idx):
                for row_idx,row in enumerate(table_2d):
                    if (row_idx in header_idx)&(row_idx!=header_idx[-1]):
                        row+=[table_2d[row_idx][col_idx],table_2d[row_idx][col_idx]]
                    elif (row_idx in header_idx)&(row_idx==header_idx[-1]):
                        row+=split_format(pattern,row[col_idx])
                    elif row_idx in superrow_idx:
                        row+=[table_2d[row_idx][col_idx],table_2d[row_idx][col_idx]]
                    else:
                        row+=split_format(pattern,row[col_idx])
            pattern=None


    # ## store in json

    # In[208]:


    def get_headers(t):
        idx_list = []
        for idx,row in enumerate(t.findAll('tr')):
            if row.findAll('th'):
                idx_list.append(idx)
        return idx_list

    def get_superrows(t):
        idx_list = []
        for idx,row in enumerate(t):
            if idx not in get_headers(t):
                if check_superrow(row):
                    idx_list.append(idx)
        return idx_list


    # In[209]:


    def table2dict(table_2d):
        headers = [table_2d[i] for i in header_idx]
        tmp_list = []
        superrow = ''
        if table_2d==None:
            return None
        for r_idx,row in enumerate(table_2d):
            if r_idx not in header_idx:
                if r_idx in superrow_idx:
                    superrow = row
                else:
                    tmp_list.append({'headers':headers,
                                    'superrow':superrow, 
                                    'row': row,})
        return tmp_list


    # In[210]:


    table_json = table2dict(table_2d)


    # In[213]:

    with open(os.path.join(target_dir,"{}_{}.json".format(pmc,caption)), "w") as outfile: 
        json.dump(table_json, outfile)

