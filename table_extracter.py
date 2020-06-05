#!/usr/bin/env python
# coding: utf-8
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
from utils import *

def table_to_2d(t):
    """
    transform a table to single cells
    ––––––––––––––––––––––––––––––––––––––––––––––––––
    params: t, soup object of table
    return: table 
    """

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

def check_superrow(row):
    """
    check if the current row is a superrow
    ––––––––––––––––––––––––––––––––––––––––––––––––––
    params: row, list object
    return: bool
    """
    if len(set([i for i in row if (str(i)!='')&(str(i)!='\n')&(str(i)!='None')]))==1:
        return True
    else:
        return False

def find_format(header):
    """
    determine if there exists a pattern in the header cell
    ––––––––––––––––––––––––––––––––––––––––––––––––––
    params: header, single header str
    return: pattern, regex object 
    """
    #     parts = nltk.tokenize.word_tokenize(header)
    a = re.split(r'[:|/,;]', header)
    b = re.findall(r'[:|/,;]', header)
    parts = []
    for i in range(len(b)):
        parts+=[a[i],b[i]]
    parts.append(a[-1])

    
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
    """
    check if the element conforms to the regex pattern
    ––––––––––––––––––––––––––––––––––––––––––––––––––
    params: pattern
            s
    return: bool
    """
    if re.search(pattern,s):
        return True
    return False

def split_format(pattern,s):
#     return pattern.split(s)[1:-1]
#     return [i for i in pattern.split(s) if i not in ':|\/,;']
    return [i for i in re.split(r'[:|/,;]', s) if i not in ':|\/,;']

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

def update_json(table_json, caption, footer):
    pre_header = None
    pre_superrow = None

    table = []


    for identifier,i in enumerate(table_json):
        cur_header = i['headers']
        cur_supperrow = i['superrow']
        cur_supperrow = [x for x in cur_supperrow if x not in ['','None']][0]
        if cur_header!=pre_header:
            section = []
            table.append({'identifier':identifier, 
                          'title':caption, 
                          'columns':cur_header,
                          'section':section})
        elif cur_header==pre_header:
            section = table[-1]['section']

        results = i['row']
        section_name = cur_supperrow
        if cur_supperrow!=pre_superrow:
            section.append({'section_name':section_name, 
                            'results': [results]})
        elif cur_supperrow==pre_superrow:

            section[-1]['results'].append(results)

        pre_header = cur_header
        pre_superrow = cur_supperrow


    new_json = {'table':table,'footer':footer}
    return new_json

if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--pbs_index", type=int, help="pbs index/the file index")
    parser.add_argument("-b", "--base_dir", help="base directory for html files")
    parser.add_argument("-t", "--target_dir", help="target directory for output")

    args = parser.parse_args()
    pbs_index = args.pbs_index
    base_dir = args.base_dir
    target_dir = args.target_dir

    file_list = get_files(base_dir)

    # # Load Soup
    filepath = file_list[pbs_index]
    pmc = filepath.split('/')[-1].strip('.html')
    with open(filepath,'r') as f:
            text = f.read()
    soup = BeautifulSoup(text, 'html.parser')


    # # Preprocssing
    for e in soup.find_all(attrs={'style':['display:none','visibility:hidden']}):
        e.extract()

    # what to do with in sentence reference
    for ref in soup.find_all(class_=['supplementary-material','figpopup','popnode','bibr']):
        ref.extract()

    process_supsub(soup)
    process_em(soup)

    # # One table

    for table_num, table in enumerate(soup.find_all('table',recursive=True)): 
        # ## caption and footer
        caption = table.find_previous('div','caption').get_text()
        footer = [i.get_text() for i in table.parent.find_next_siblings('div','tblwrap-foot')]

        header_idx = []
        for idx,row in enumerate(table.findAll('tr')):
            if row.findAll('th'):
                header_idx.append(idx)

        # ## span table to single-cells
        table_2d = table_to_2d(table)

        ## find superrows
        superrow_idx = []
        if table_2d!=None:
            for row_idx,row in enumerate(table_2d):
                if row_idx not in header_idx:
                    if check_superrow(row):
                        superrow_idx.append(row_idx)

        # ## split pattern
        for col_idx,th in enumerate(table_2d[header_idx[-1]]):
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
                pattern = None


        table_json = table2dict(table_2d)

        # ## merge headers
        sep = '<!>'
        for row in table_json:
            headers = row['headers']
            
            new_header = []
            for col_idx in range(len(headers[0])):
                new_element = ''
                for r_idx in range(len(headers)):
                    new_element += headers[r_idx][col_idx]+sep
                new_element = new_element.rstrip(sep)
                new_header.append(new_element)
            row['headers'] = new_header

        new_json = update_json(table_json, caption, footer)

        # ## store in json
        is_dir = os.path.isdir(os.path.join(target_dir,"{}_tables".format(pmc)))
        if not is_dir:
            os.mkdir(os.path.join(target_dir,"{}_tables".format(pmc)))
            
        with open(os.path.join(target_dir,pmc,"{}_table{}.json".format(pmc,table_num)), "w") as outfile: 
            json.dump(table_json, outfile)

