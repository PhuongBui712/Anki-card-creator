import os
import re

from global_var import *
from utils import *


def get_word_panel_by_type(word, word_type=None, dictionary_url=CAMBRIDGE_URL):
    word_page_url = CAMBRIDGE_URL + r'/dictionary/english/' + word.replace(' ', '-').lower()
    word_page_src, status_code = get_page_src(word_page_url)

    if not status_code:
        return None
    
    # select panel by word types
    word_panels = word_page_src.find_all('div', {'class': 'pr dictionary',
                                                 'role': 'tabpanel'})
    res_panel = word_panels[0]
    if word_type:
        for panel in word_panels:
            type = panel.find('span', {'class': 'pos dpos'}).get_text()
            if type == word_type:
                return panel
    
    return res_panel


def get_sound(soup, file_path, dictionary_url=cambridge_url, included_pattern=None):
    if os.path.exists(file_path):
        return

    # get all download source
    source_tags = soup.find_all('source')
    download_url = source_tags[0]['src']
    if included_pattern:
        for tag in source_tags:
            if re.search(included_pattern, tag['src']):
                download_url = tag['src']
                break
             
    download_url = dictionary_url + download_url

    audio = get_url(download_url, get_raw_data=True)
    with open(file_path, 'wb') as f:
        f.write(audio)

    return file_path


def get_phonetic(soup):
    phonetic = None
    phonetic_tags = soup.find_all('span', {'class': 'pron dpron'})
    if phonetic_tags:
        return phonetic_tags[1].get_text()
    
    return phonetic


def get_english_meaning(soup):
    meaning = soup.find('div', 'def ddef_d db').get_text().strip()
    if not meaning[-1].isalpha():
        meaning = meaning[:-1]
    
    return meaning


def get_examples(soup):
    examples_box = soup.find('div', 'def-body ddef_b')
    if not examples_box:
        return None
    
    examples = examples_box.find_all('div', 'examp dexamp')
    res = []
    for exp in examples:
        use_case = exp.find('span', 'lu dlu')
        exp_sentence = exp.find('span', 'eg deg').get_text()

        complete_exp_sentence = '- '
        if use_case:
            complete_exp_sentence += f'({use_case.get_text()}) | '
        
        complete_exp_sentence += exp_sentence + '\n\n'
        res.append(complete_exp_sentence)

    return ''.join(res)