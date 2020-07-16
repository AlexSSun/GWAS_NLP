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
    # https://stackoverflow.com/questions/48393253/how-to-parse-table-with-rowspan-and-colspan
    
    rows = t.find_all('tr')

    # first scan, see how many columns we need
    n_cols = sum([int(i.attrs['colspan']) for i in t.find('tr').findAll(['th','td'])])
    
    # build an empty matrix for all possible cells
    table = [[''] * n_cols for row in rows]

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
            # clean the cell
            value = value.strip().replace('\u2009',' ')
#             value = value.replace('\u2009',' ')
            if value.startswith('(') and value.endswith(')'):
                value = value[1:-1]
            if re.match(pval_regex,value):
#                 value = value.replace(' × 10_','e').replace('×10_','e').replace('−','-')
                value = re.sub(r'(\s{0,1})[*××xX](\s{0,1})10_','e',value).replace('−','-')
#             if re.match('^((\d+.\d+)|(\d+))[eE]([−-]{0,1}\d+)$',value):
#                 value = float(value)
            try:
                value = float(value.replace('−','-').replace('–','-').replace(',',''))
            except:
                value = value
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
    determine if there exists a splittable pattern in the header cell

    Args:
        header: single header str

    Returns:
        pattern: regex object 

    Raises:
        KeyError: Raises an exception.
    """

    if header=='':
        return None
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

    Args:
        header: single header str
        s: element in string format

    Returns:
        result: bool

    Raises:
        KeyError: Raises an exception.
    """

    if re.search(pattern,s):
        return True
    return False

def split_format(pattern,s):
    """
    split s according to regex pattern

    Args:
        pattern: regex object 
        s: element in string format

    Returns:
        list of substrings

    Raises:
        KeyError: Raises an exception.
    """
#     return pattern.split(s)[1:-1]
#     return [i for i in pattern.split(s) if i not in ':|\/,;']
    return [i for i in re.split(r'[:|/,;]', s) if i not in ':|\/,;']

def get_headers(t):
    """
    identify headers from a table

    Args:
        t: BeautifulSoup object of table

    Returns:
        idx_list: a list of header index

    Raises:
        KeyError: Raises an exception.
    """
    idx_list = []
    for idx,row in enumerate(t.findAll('tr')):
        if row.findAll('th'):
            idx_list.append(idx)
    return idx_list

def get_superrows(t):
    """
    determine if there exists a splittable pattern in the header cell

    Args:
        t: BeautifulSoup object of table

    Returns:
        idx_list: a list of superrow index

    Raises:
        KeyError: Raises an exception.
    """
    idx_list = []
    for idx,row in enumerate(t):
        if idx not in get_headers(t):
            if check_superrow(row):
                idx_list.append(idx)
    return idx_list

def is_number(s):
    try:
        float(s.replace(',',''))
        return True
    except ValueError:
        return False

def is_mix(s):
    if any(char.isdigit() for char in s):
        if any(char for char in s if char.isdigit()==False):
            return True
    return False

def is_text(s):
    if any(char.isdigit() for char in s):
        return False
    return True

def table2json(table_2d, header_idx, subheader_idx, superrow_idx, table_num, caption, footer):
    tables = []
    sections = []
    cur_table = {}
    cur_section = {}

    pre_header = []
    pre_superrow = None
    cur_header = ''
    cur_superrow = ''
    for row_idx,row in enumerate(table_2d):
        if not any([i for i in row if i not in ['','None']]):
            continue
        if row_idx in header_idx:
            cur_header = [table_2d[i] for i in [i for i in subheader_idx if row_idx in i][0]]
        elif row_idx in superrow_idx:
            cur_superrow = [i for i in row if i not in ['','None']][0]
        else:      
            if cur_header!=pre_header:
                sections = []
                pre_superrow = None
                cur_table = {'identifier':str(table_num+1), 
                             'title':caption, 
                             'columns':cur_header,
                             'section':sections,
                             'footer':footer}
                tables.append(cur_table)
            elif cur_header==pre_header:
                cur_table['section'] = sections
            if cur_superrow!=pre_superrow:
                cur_section = {'section_name':cur_superrow, 
                               'results': [row]}
                sections.append(cur_section)
            elif cur_superrow==pre_superrow:
                cur_section['results'].append(row)

            pre_header = cur_header
            pre_superrow = cur_superrow

    if len(tables)>1:
        for table_idx,table in enumerate(tables):
            table['identifier'] += '.{}'.format(table_idx+1)
    return tables

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
    tables = []
    for table_num, table in enumerate(soup.find_all('table',recursive=True)): 

        try:
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

            # ## identify section names in index column
            if superrow_idx==[]:
            # if (superrow_idx==[])&(table_2d[0][0]==''):
                first_col = [row[0] for row in table_2d]
                first_col_vals = [i for i in first_col if first_col.index(i) not in header_idx] 
                unique_vals = set([i for i in first_col_vals if i not in ['','None']])
                if len(unique_vals)<=len(first_col_vals)/2:
                    section_names = list(unique_vals)
                    for i in section_names:
                        superrow_idx.append(first_col.index(i))
                    n_cols = len(table_2d[0])
                    for idx,val in zip(superrow_idx, section_names):
                        table_2d = table_2d[:idx]+[[val]*n_cols]+table_2d[idx:]
                    #update superrow_idx after superrow insertion
                    superrow_idx = []
                    first_col = [row[0] for row in table_2d]
                    for i in section_names:
                        superrow_idx.append(first_col.index(i))
                    for row in table_2d:
                        row.pop(0)

            ## Identify subheaders
            value_idx = [i for i in range(len(table_2d)) if i not in header_idx+superrow_idx]
            col_type = []
            for col_idx in range(len(table_2d[0])):
                cur_col = [i[col_idx] for i in table_2d]
                num_cnt = 0
                txt_cnt = 0
                mix_cnt = 0
                for cell in cur_col:
                    cell = str(cell).lower()
                    if cell in ['none', '', '-',]:
                        continue
                    elif is_number(cell):
                        num_cnt+=1
                    elif is_mix(cell):
                        mix_cnt+=1
                    elif is_text(cell):
                        txt_cnt+=1
                if max(num_cnt,txt_cnt,mix_cnt)==num_cnt:
                    col_type.append('num')
                elif max(num_cnt,txt_cnt,mix_cnt)==txt_cnt:
                    col_type.append('txt')
                else:
                    col_type.append('mix')
            subheader_idx = []
            for row_idx in value_idx:
                cur_row = table_2d[row_idx]
                unmatch_cnt = 0
                for col_idx in range(len(cur_row)):
                    cell = str(cur_row[col_idx]).lower()
                    if is_text(cell) and col_type[col_idx]!='txt' and cell not in ['none', '', '-',]:
                        unmatch_cnt+=1
                if unmatch_cnt>=len(cur_row)/2:
                    subheader_idx.append(row_idx)
            header_idx+=subheader_idx

            subheader_idx = []
            tmp = [header_idx[0]]
            for i,j in zip(header_idx,header_idx[1:]):
                if j==i+1:
                    tmp.append(j)
                else:
                    subheader_idx.append(tmp)
                    tmp=[j]
            subheader_idx.append(tmp)

            # ## split cell pattern
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

            cur_table = table2json(table_2d, header_idx, subheader_idx, superrow_idx, table_num, caption, footer)

            # ## merge headers
            sep = '<!>'
            for table in cur_table:
                headers = table['columns']
                
                new_header = []
                for col_idx in range(len(headers[0])):
                    new_element = ''
                    for r_idx in range(len(headers)):
                        new_element += headers[r_idx][col_idx]+sep
                    new_element = new_element.rstrip(sep)
                    new_header.append(new_element)
                table['columns'] = new_header

            tables+=cur_table
        except Exception as e:
            print('table not extracted ', table_num)
            print(e)

    table_json = {'tables':tables}
    
    if not os.path.isdir(target_dir):
        os.makedirs(target_dir)

    with open(os.path.join(target_dir,"{}_tables.json".format(pmc)), "w") as outfile: 
        json.dump(table_json, outfile,ensure_ascii=False)