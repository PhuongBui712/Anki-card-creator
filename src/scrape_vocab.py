import os
import json
import re
import warnings
from tqdm import tqdm
import pandas as pd
from pandas import DataFrame
from bs4 import BeautifulSoup, Tag, NavigableString
from typing import Optional, Literal
from global_var import *
from utils import *


def is_valid_cambridge_url(url: str) -> bool:
    # This function is temporarily inappropriate
    last_sub_path = url.split("/")[-1]
    if last_sub_path.startswith("?q="):
        warnings.warn(f"Invalid word {last_sub_path[3:]}")


def get_full_word_type(word_type: str) -> str:
    if word_type == "n":
        res = "noun"
    elif word_type == "v":
        res = "verb"
    elif word_type == "adj":
        res = "adjective"
    elif word_type == 'adv':
        res = "adverb"
    else:
        return word_type

    return res


def create_cloze(word: str) -> str:
    return word[0] + re.sub(r"\w", "_", word[1:])


def check_existed(entry, scraped_df: DataFrame) -> bool:
    return (
        (scraped_df.vocabulary == entry.vocabulary) & (scraped_df.type == entry.type)
    ).any()


def get_dictionary_url(
    dictionary: Literal["cambridge", "oxford"] = "cambridge",
    get_only_domain: bool = True,
) -> str:
    url = CAMBRIDGE_URL if dictionary == "cambridge" else OXFORD_URL
    path = ""
    if not get_only_domain:
        path = (
            "/dictionary/english/"
            if dictionary == "cambridge"
            else "/definition/english/"
        )

    return url + path


def get_word_panel_by_type(
    word: str,
    word_type: Optional[str] = None,
    dictionary: Literal["cambridge", "oxford"] = "cambridge",
    check_url: Callable[[str, str], bool] = None,
) -> Union[BeautifulSoup, None]:
    word_page_url = (
        get_dictionary_url(dictionary, get_only_domain=False)
        + word.replace(" ", "-").lower()
    )
    
    if check_url:
        word_page_src = get_url(word_page_url, check_url=check_url)
    else:
        word_page_src = get_url(word_page_url)

    if word_page_src is not None:
        # select panel by word types
        word_panels = word_page_src.find_all(
            "div", {"class": "pr entry-body__el"}
        )
        res_panel = word_panels[0]
        if word_type:
            for i, panel in enumerate(word_panels):
                type = panel.find("span", {"class": "pos dpos"}).get_text()
                if type == word_type:
                    return panel

        return res_panel
    return None


def get_sound(
    soup: BeautifulSoup,
    dictionary_url: str = CAMBRIDGE_URL,
    pronunciation_type: Literal["uk", "us"] = "us",
) -> str:
    span_tags = soup.find_all('')
    # get all download source
    source_tags = soup.find_all("source")
    audio_url = source_tags[0]["src"]
    for tag in source_tags:
        if re.search(pronunciation_type, tag["src"]):
            audio_url = tag["src"]
            break

    audio_url = dictionary_url + audio_url
    audio = get_url(audio_url, get_raw_data=True)

    audio_name = get_file_name_from_url(audio_url)
    audio_path = get_media_path(audio_name, "audio")
    with open(audio_path, "wb") as f:
        f.write(audio)

    return f"[sound:{audio_path}]"


def get_phonetic(soup) -> str:
    phonetic = None
    phonetic_tags = soup.find_all("span", {"class": "pron dpron"})
    if phonetic_tags:
        try:
            phonetic = phonetic_tags[1].get_text()
        except:
            phonetic = phonetic_tags[0].get_text()

    return phonetic


def get_english_meaning(soup) -> str:
    meaning = soup.find("div", "def ddef_d db").get_text().strip()
    if not meaning[-1].isalpha():
        meaning = meaning[:-1]

    return meaning


def get_examples(soup: BeautifulSoup, max_example: int = 5):
    examples_box = soup.find("div", "def-body ddef_b")
    if not examples_box:
        return None

    example_tags = examples_box.find_all("div", "examp dexamp")
    examples = []
    for i, exp in enumerate(example_tags):
        if i >= max_example:
            break
        exp_usecase = ""

        # handle usecase
        use_case = exp.find("span", "gram dgram") or exp.find("a", "lu dlu")
        if use_case:
            exp_usecase += f'<span class="example_usecase">{use_case.text}</span>'

        # handle example sentence
        exp_sentence = "  "
        exp_sentence_tag = exp.find("span", "eg deg")
        for child in exp_sentence_tag.children:
            if isinstance(child, NavigableString):
                exp_sentence += child.text
            else:
                if child.name == "span" and child.attrs["class"] == "b db".split():
                    exp_sentence += (
                        f'<span class="example_highligh">{child.text}</span>'
                    )
                else:
                    exp_sentence += child.text

        exp_sentence = f'<span class="example_sentence">{exp_sentence}</span>'
        exp_tag = f'<div class="example">{exp_usecase}{exp_sentence}</div>'
        examples.append(exp_tag)

    return "\n".join(examples)


def get_images(soup: BeautifulSoup, dictionary_url: str = CAMBRIDGE_URL):
    image_tag = soup.find("script", attrs={"type": "application/json"})
    if image_tag:
        image_url = dictionary_url + json.loads(image_tag.text)["src"]
        image = get_url(image_url, get_raw_data=True)

        image_name = get_file_name_from_url(image_url)
        image_path = get_media_path(image_name, "image")
        with open(image_path, "wb") as f:
            f.write(image)

        relative_path = "./" + os.path.join(
            os.getenv("ILLUSTRATIVE_IMAGE_PATH"), image_name
        )
        return f"<img src='{relative_path}' />"

    return ""


def scrape_vocab(vocabs: DataFrame, scraped_vocab_path: Optional[str] = None):
    # preprocess
    vocabs["vocabulary"] = vocabs.vocabulary.str.lower()
    vocabs["type"] = vocabs.type.apply(lambda x: get_full_word_type(x))
    vocabs['vietnamese meaning'] = vocabs['vietnamese meaning'].str.replace('\n', '<br>')

    # check existence
    new_vocabs = vocabs.copy()
    if scraped_vocab_path:
        existed_vocabs = pd.read_csv(scraped_vocab_path, names=REORDERED_HEADER)
        mask = vocabs.apply(lambda x: check_existed(x, existed_vocabs), axis=1)
        new_vocabs = new_vocabs.iloc[~mask.to_numpy()]

    # scrape
    cloze = []
    phonetic = []
    pronounce = []
    image = []
    engmean = []
    example = []
    unscrawled_idx = []
    for i, w in enumerate(
        tqdm(zip(new_vocabs.vocabulary, new_vocabs.type), total=len(new_vocabs))
    ):
        word, word_type = w
        # locate panel
        panel_soup = get_word_panel_by_type(word, word_type)
        if panel_soup is None:
            unscrawled_idx.append(i)
            continue

        # crawl essential data
        cloze.append(create_cloze(word))
        phonetic.append(get_phonetic(panel_soup))
        pronounce.append(get_sound(panel_soup))
        image.append(get_images(panel_soup))
        engmean.append(get_english_meaning(panel_soup))
        example.append(get_examples(panel_soup))

    # update new vocabularies
    common_len = len(cloze)
    assert (
        len(phonetic) == common_len
        and len(pronounce) == common_len
        and len(engmean) == common_len
        and len(example) == common_len
    ), "Appearing error(s) while scrapeing"

    # filter unscrawled word
    new_vocabs = new_vocabs.iloc[[i for i in range(len(new_vocabs)) if i not in unscrawled_idx]]
    for data, col in zip(
        (cloze, phonetic, pronounce, image, engmean, example), PROCESS_HEADER[3:]
    ):
        new_vocabs[col] = data

    # reorder columns
    new_vocabs = new_vocabs[REORDERED_HEADER]

    # Update the craped vocabularies
    if scraped_vocab_path:
        lastest_vocab = pd.concat((new_vocabs, existed_vocabs), ignore_index=True)
    else:
        lastest_vocab = new_vocabs

    return (new_vocabs, vocabs.iloc[unscrawled_idx]), lastest_vocab
