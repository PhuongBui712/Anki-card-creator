import concurrent.futures
import json
import os
import re
import warnings
from typing import Literal, Optional, Callable

import pandas as pd
from bs4 import BeautifulSoup, NavigableString
from pandas import DataFrame
from tqdm import tqdm

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
    elif word_type == "adv":
        res = "adverb"
    elif word_type == "prep":
        res = "preposition"
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
        word_panels = word_page_src.find_all("div", {"class": "pr entry-body__el"})
        res_panel = word_panels[0]
        if word_type:
            for i, panel in enumerate(word_panels):
                type = panel.find("span", {"class": "pos dpos"}).get_text()
                if type == word_type.split(","):
                    return panel

        return res_panel
    return None


def get_sound(
    soup: BeautifulSoup,
    filename: str,
    dictionary_url: str = CAMBRIDGE_URL,
    pronunciation_type: Literal["uk", "us"] = "us",
) -> str:
    # get all download source
    source_tags = soup.find_all("source")
    audio_url = source_tags[0]["src"]
    for tag in source_tags:
        if re.search(pronunciation_type, tag["src"]) and re.search("mp3", tag["src"]):
            audio_url = tag["src"]
            break

    audio_url = dictionary_url + audio_url

    audio_name = f"{filename}.mp3"
    audio_path = get_media_path(audio_name, "audio")

    audio = get_url(audio_url, stream=True, return_type="response")
    with open(audio_path, "wb") as file:
        for chunk in audio.iter_content(chunk_size=1024):
            if chunk:
                file.write(chunk)

    # audio = get_url(audio_url, return_type)
    # with open(audio_path, "wb") as f:
    #     f.write(audio)

    return f"[sound:{audio_path}]"


def get_phonetic(soup) -> str:
    phonetic = None
    phonetic_tags = soup.find_all("span", {"class": "pron dpron"})
    if phonetic_tags:
        try:
            phonetic = phonetic_tags[1].get_text()
        except Exception:
            phonetic = phonetic_tags[0].get_text()

    return phonetic


def get_english_meaning(soup) -> str:
    meaning = soup.find("div", "def ddef_d db").get_text().strip()
    if not meaning[-1].isalpha():
        meaning = meaning[:-1]

    return meaning


def get_examples(soup: BeautifulSoup, max_example: int = 3):
    examples_box = soup.find("div", "def-body ddef_b")

    if examples_box:
        example_tags = examples_box.find_all("div", "examp dexamp")
    else:
        example_tags = []

    if not examples_box or not example_tags:
        # Try to find examples in the expanded section
        expanded_section = soup.find("section", {"expanded": ""})
        if expanded_section:
            example_tags = expanded_section.find_all("li", {"class": "eg dexamp hax"})
        else:
            return None

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
        if examples_box and exp.find("span", "eg deg"):
            exp_sentence_tag = exp.find("span", "eg deg")
            for child in exp_sentence_tag.children:
                if isinstance(child, NavigableString):
                    exp_sentence += child.text
                else:
                    if (
                        child.name == "span"
                        and child.attrs.get("class") == "b db".split()
                    ):
                        exp_sentence += (
                            f'<span class="example_highligh">{child.text}</span>'
                        )
                    else:
                        exp_sentence += child.text
        else:
            # Extract example sentence from expanded section
            exp_sentence += exp.get_text()

        exp_sentence = f'<span class="example_sentence">{exp_sentence}</span>'
        exp_tag = f'<div class="example">{exp_usecase}{exp_sentence}</div>'
        examples.append(exp_tag)

    return "\n".join(examples)


def get_images(soup: BeautifulSoup, dictionary_url: str = CAMBRIDGE_URL):
    image_tag = soup.find("script", attrs={"type": "application/json"})
    if image_tag:
        image_url = dictionary_url + json.loads(image_tag.text)["src"]
        image = get_url(image_url, return_type="raw")

        image_name = get_file_name_from_url(image_url)
        image_path = get_media_path(image_name, "image")
        with open(image_path, "wb") as f:
            f.write(image)

        relative_path = "./" + os.path.join(
            os.getenv("ILLUSTRATIVE_IMAGE_PATH"), image_name
        )
        return f"<img src='{relative_path}' />"

    return ""


def scrape_single_vocab(word: str, word_type: str):
    """Scrapes data for a single vocabulary entry."""
    panel_soup = get_word_panel_by_type(word, word_type)
    if panel_soup is None:
        return None, None, None, None, None, None

    cloze = create_cloze(word)
    phonetic = get_phonetic(panel_soup)
    pronounce = get_sound(panel_soup, word)
    image = get_images(panel_soup)
    engmean = get_english_meaning(panel_soup)
    example = get_examples(panel_soup)

    return cloze, phonetic, pronounce, image, engmean, example


def scrape_vocab(vocabs: DataFrame, scraped_vocab_path: Optional[str] = None):
    # preprocess
    vocabs["vocabulary"] = vocabs.vocabulary.str.lower()
    vocabs["type"] = vocabs.type.apply(lambda x: get_full_word_type(x))
    vocabs["vietnamese meaning"] = vocabs["vietnamese meaning"].str.replace(
        "\n", "<br>"
    )

    # check existence
    new_vocabs = vocabs.copy()
    if scraped_vocab_path:
        existed_vocabs = pd.read_csv(scraped_vocab_path, names=REORDERED_HEADER)
        mask = vocabs.apply(lambda x: check_existed(x, existed_vocabs), axis=1)
        new_vocabs = new_vocabs.iloc[~mask.to_numpy()]

    # scrape
    cloze = [None for _ in range(len(new_vocabs))]
    phonetic = [None for _ in range(len(new_vocabs))]
    pronounce = [None for _ in range(len(new_vocabs))]
    image = [None for _ in range(len(new_vocabs))]
    engmean = [None for _ in range(len(new_vocabs))]
    example = [None for _ in range(len(new_vocabs))]
    unscrawled_idx = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=40) as executor:
        futures = {
            executor.submit(scrape_single_vocab, word, word_type): (i, word, word_type)
            for i, (word, word_type) in enumerate(
                zip(new_vocabs.vocabulary, new_vocabs.type)
            )
        }

        for future in tqdm(
            concurrent.futures.as_completed(futures), total=len(futures)
        ):
            i, word, word_type = futures[future]
            try:
                c, ph, pr, im, em, ex = future.result()

                if c:
                    cloze[i] = c
                    phonetic[i] = ph
                    pronounce[i] = pr
                    image[i] = im
                    engmean[i] = em
                    example[i] = ex
                else:
                    unscrawled_idx.append(i)
            except Exception as e:
                print(f"Error scraping {word} ({word_type}): {e}")
                unscrawled_idx.append(i)

    # remove None
    cloze = [_ for i, _ in enumerate(cloze) if i not in unscrawled_idx]
    phonetic = [_ for i, _ in enumerate(phonetic) if i not in unscrawled_idx]
    pronounce = [_ for i, _ in enumerate(pronounce) if i not in unscrawled_idx]
    image = [_ for i, _ in enumerate(image) if i not in unscrawled_idx]
    engmean = [_ for i, _ in enumerate(engmean) if i not in unscrawled_idx]
    example = [_ for i, _ in enumerate(example) if i not in unscrawled_idx]

    # update new vocabularies
    common_len = len(cloze)
    if common_len > 0:
        assert (
            len(phonetic) == common_len
            and len(pronounce) == common_len
            and len(engmean) == common_len
            and len(example) == common_len
        ), "Appearing error(s) while scraping"

    # filter unscrawled word
    new_vocabs_index = [i for i in range(len(new_vocabs)) if i not in unscrawled_idx]
    new_vocabs = new_vocabs.iloc[new_vocabs_index]

    # Add data only if there are successfully scraped words
    if common_len > 0:
        for data, col in zip(
            (cloze, phonetic, pronounce, image, engmean, example), PROCESS_HEADER[3:]
        ):
            new_vocabs[col] = data

    # reorder columns
    new_vocabs = new_vocabs[REORDERED_HEADER]

    # Update the scraped vocabularies
    if scraped_vocab_path:
        lastest_vocab = pd.concat((new_vocabs, existed_vocabs), ignore_index=True)
    else:
        lastest_vocab = new_vocabs

    unscrawled_vocabs = vocabs.iloc[unscrawled_idx]
    return (new_vocabs, unscrawled_vocabs), lastest_vocab
