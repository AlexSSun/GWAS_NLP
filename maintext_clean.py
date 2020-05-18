#!/usr/bin/env python
# coding: utf-8

# In[29]:


from IPython import display

import os
import re
from html.parser import HTMLParser
from bs4 import BeautifulSoup
from bs4 import element
from itertools import product
import numpy as np
import pandas as pd
import json


# In[30]:


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
            


# In[31]:


def process_caption(soup):
    for div in soup.find_all('div', attrs='caption'):
        div.extract()

def process_table_figures(soup):
    for div in soup.find_all('div',attrs=['table-wrap','table','fig']):
        div.extract()
        
        


# In[ ]:





# In[32]:



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
# base_dir = '../NLP-GWAS/Dev Set/'
base_dir = '../NLP-GWAS/Test Set/'

file_list = get_files(base_dir)


# In[33]:


def extract_text(soup):
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


# In[ ]:





# In[34]:


# def extract_text(soup):
#     h1 = soup.find_all('h1',"content-title")[0].get_text()
#     main_text = []
#     paragraphs = soup.find_all('p',attrs='p')
# #     paragraphs =soup.find_all('p',attrs={'id':re.compile('(__|_|)(p|P)\d+')})

#     for p in paragraphs:
#         h2 = p.find_previous('h2','head')
#         if h2:
#             h2=h2.get_text()
#         else:
#             h2=''
#         h3 = p.find_previous_sibling('h3',attrs={'id':re.compile('S[0-9]title')})
#         if h3:
#             h3=h3.get_text()
#         else:
#             h3=''
#         main_text.append([h2,h3,p.get_text()])

#     result = {h1:main_text}    
#     return result


# In[35]:


# filepath = file_list[1]


# In[36]:


filepath = '../NLP-GWAS/Dev Set/1-100/PMC5968830.html'


# In[37]:


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
process_caption(soup)
process_table_figures(soup)

result = extract_text(soup)
print(filepath, len(list(result.values())[0]))


# In[ ]:





# In[38]:


maintext_dict = {}


# In[39]:


for i,filepath in enumerate(file_list):
    
    if i%10==0:
        print("\rProgress {:2.1%}".format(i / len(file_list)))
        display.clear_output(wait=True)
    
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


# In[40]:


[i for i in file_list if 'PMC5968830' in i]


# In[41]:


target_dir = '../output/maintext/'


# In[42]:


for k,v in maintext_dict.items():
    with open(os.path.join(target_dir,"{}_maintext.json".format(k)), "w") as outfile: 
        json.dump(v, outfile) 


# In[ ]:





# In[ ]:




