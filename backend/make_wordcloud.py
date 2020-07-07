import script_constructor as sc
import re
import random
import unicodedata
import util
from contractions import CONTRACTION_MAP 
from nltk.corpus import stopwords
from gensim.corpora import Dictionary
from gensim.models import TfidfModel
from wordcloud import WordCloud, get_single_color_func
from nltk.tokenize import word_tokenize
from nltk.stem.porter import PorterStemmer
from collections import defaultdict
import string as String
import base64
from io import BytesIO
import numpy as np
from PIL import Image


def generate_corpus(script, character_name, analyze_action_lines):
    if character_name != None:
        return script.get_all_text_from_one_character(character_name)
    elif analyze_action_lines:
        return script.get_all_text_from_action_lines()
    else:
        return script.get_whole_script_as_corpus()

# thanks to https://towardsdatascience.com/creating-word-clouds-with-python-f2077c8de5cc
def expand_contractions(text, contraction_mapping=CONTRACTION_MAP):
    text = text.strip(' ' + String.punctuation)

    # if 'mere' in text:
    #     print( text)
    contractions_pattern = re.compile('({})'.format('|'.join(contraction_mapping.keys())), 
                                      flags=re.IGNORECASE|re.DOTALL)
    def expand_match(contraction):
        match = contraction.group(0)
        first_char = match[0]
        expanded_contraction = contraction_mapping.get(match)\
                                if contraction_mapping.get(match)\
                                else contraction_mapping.get(match.lower())                       
        expanded_contraction = first_char+expanded_contraction[1:]
        return expanded_contraction
        
    expanded_text = contractions_pattern.sub(expand_match, text)
    expanded_text = re.sub("'", "", expanded_text)
    return expanded_text 

def replace_tail_apostrophes(text):
    return re.sub('in’', 'ing', text)

def get_common_surface_form(original_corpus, stemmer):
    counts = defaultdict(lambda : defaultdict(int))
    surface_forms = {}

    for document in original_corpus:
        for token in document:
            stemmed = stemmer.stem(token)
            counts[stemmed][token] += 1

    for stemmed, originals in counts.items():
        surface_forms[stemmed] = max(originals, 
                                     key=lambda i: originals[i])

    return surface_forms

# thanks to https://www.scss.tcd.ie/~munnellg/projects/visualizing-text.html
def generate_tfidf_cloud(script, character_name=None, analyze_action_lines=False):
    corpus = generate_corpus(script, character_name, analyze_action_lines)
    corpus = util.remove_stop_words(corpus, stopwords.words("english")+stopwords.words("spanish")+['hey', 'hello', 'sure', 'yeah', 'whoa', 'woah'])
    cleaned_untokenized_corpus = clean_wordcloud_corpus(corpus)
    stemmed_corpus = []
    original_corpus = []
    # print(stopwords.words("english"))
    for e in cleaned_untokenized_corpus:
        tokens = word_tokenize(e)
        # print(tokens)
        
        stemmed = util.get_stemmed_text(tokens)
        stemmed_corpus.append(stemmed)
        original_corpus.append(tokens)
        
    dictionary = Dictionary(stemmed_corpus)
    counts = get_common_surface_form(original_corpus, PorterStemmer())
    vectors = [dictionary.doc2bow(text) for text in stemmed_corpus]
    tfidf = TfidfModel(vectors)
    weights = []
    for e in vectors:
        weights.extend(tfidf[e])
    weights_dict = {}
    for pair in weights:
        if (counts[dictionary[pair[0]]] not in stopwords.words("english")+stopwords.words("spanish")+['hey', 'hello', 'sure', 'yeah', 'whoa', 'woah']):
            weights_dict[counts[dictionary[pair[0]]]] = pair[1] 
    # print(weights)
    # for pair in weights:
    #     # if ('hell' in pair[0]):
    #     print(pair)
    # {k: v for k, v in sorted(weights_dict.items(), key=lambda item: item[1])}
    # print({k: v for k, v in sorted(weights_dict.items(), key=lambda item: item[1])})

    mask = np.array(Image.open("mask.png"))


    wc = WordCloud(
    background_color="#0f0f0f",
    # background_color='ghostwhite',
    max_words=300,
    max_font_size=200,
    # colormap=random.choice([
    #     'Paired', 'Set1', 'Set2', 'Set3'
    # ]),
    colormap=random.choice([
            'PiYG', 'PRGn', 'BrBG', 'PuOr',
            'RdYlBu', 'RdYlGn', 'Spectral', 'coolwarm', 'bwr', 'seismic']),
    width = 1024,
    height = 720,
    mask=mask,
    stopwords=stopwords.words("english")+stopwords.words("spanish")+['hey', 'hello', 'sure', 'yeah', 'whoa', 'woah']
    )

    wc.generate_from_frequencies(weights_dict)

    return wc

    # vectorizer = util.getVectorizer('tfidf')
    # vectorizer.fit(corpus)
    # matrix = vectorizer.transform(corpus)
    # matrix_list = matrix.toarray().tolist()
    # vocab = list(vectorizer.vocabulary_.keys())
    # print(vectorizer.vocabulary_['hunting'])
    # cloud_dict = {}
    # for i in range(len(vocab)):
    #     cloud_dict[vocab[i]] = 0
    #     for arr in matrix_list:
    #         cloud_dict[vocab[i]] += arr[i]
    # sorted_cloud = sorted(list(cloud_dict.keys()), key=cloud_dict.get, reverse=True) 
    # for i in sorted_cloud:
    #     print(e, cloud_dict[e])
    # CHECK THIS
    # https://www.scss.tcd.ie/~munnellg/projects/visualizing-text.html



def clean_wordcloud_corpus(corpus):
    for i in range(len(corpus)):
        corpus[i] = corpus[i].lower()
        corpus[i] = expand_contractions(corpus[i])
        corpus[i] = replace_tail_apostrophes(corpus[i])
        corpus[i] = unicodedata.normalize('NFKD', corpus[i]).encode('ascii', 'ignore').decode('utf-8', 'ignore')
        corpus[i] = corpus[i].replace("--", " ").strip()
        remove_digits = False
        pattern = r'[^a-zA-Z0-9\s]' if not remove_digits else r'[^a-zA-Z\s]'    
        corpus[i] = re.sub(pattern, '', corpus[i])

    cleaned_corpus = []
    for e in corpus:
        if len(e) != 0:
            cleaned_corpus.append(e)
    return cleaned_corpus

def generateClouds(script, whole_script, action_lines, characters):
    buffered = BytesIO()
    base64clouds = []
    if whole_script:
        img = generate_tfidf_cloud(script, None, False).to_image()
        img.save(buffered, format="JPEG")
        img_str = base64.b64encode(buffered.getvalue()).decode("ascii")
        base64clouds.append(img_str)
    if action_lines:
        img = generate_tfidf_cloud(script, None, False).to_image()
        img.save(buffered, format="JPEG")
        img_str = base64.b64encode(buffered.getvalue()).decode("ascii")
        base64clouds.append(img_str)
    for c in characters:
        if c in script.characters:
            img = generate_tfidf_cloud(script, c, False).to_image()
            img.save(buffered, format="JPEG")
            img_str = base64.b64encode(buffered.getvalue()).decode("ascii")
            base64clouds.append(img_str)
    return base64clouds

# script = sc.initialize_script('Breaking Bad - Pilot')
# generate_tfidf_cloud(script, 'walt', False).to_file('clouds/walt.png')
# generate_tfidf_cloud(script, None, False).to_file('clouds/bbad.png')
# generate_tfidf_cloud(script, None, True).to_file('clouds/bbad-actions.png')

# script = sc.initialize_script('Chinatown')
# generate_tfidf_cloud(script, 'gittes', False).to_file('clouds/gittes.png')
# generate_tfidf_cloud(script, None, False).to_file('clouds/china.png')
# generate_tfidf_cloud(script, None, True).to_file('clouds/china-actions.png')

# script = sc.initialize_script('Community - Pilot')
# generate_tfidf_cloud(script, 'jeff', False).to_file('clouds/jeff.png')
# generate_tfidf_cloud(script, 'abed', False).to_file('clouds/abed.png')
# generate_tfidf_cloud(script, None, False).to_file('clouds/comm.png')
# generate_tfidf_cloud(script, None, True).to_file('clouds/comm-actions.png')

# script = sc.initialize_script('Her')
# generate_tfidf_cloud(script, 'theodore', False).to_file('clouds/theo.png')
# generate_tfidf_cloud(script, 'samantha', False).to_file('clouds/sam.png')
# generate_tfidf_cloud(script, None, False).to_file('clouds/her.png')
# generate_tfidf_cloud(script, None, True).to_file('clouds/her-actions.png')

# script = sc.initialize_script('Knives Out')
# generate_tfidf_cloud(script, 'blanc', False).to_file('clouds/blanc.png')
# generate_tfidf_cloud(script, 'marta', False).to_file('clouds/marta.png')
# generate_tfidf_cloud(script, None, False).to_file('clouds/knives.png')
# generate_tfidf_cloud(script, None, True).to_file('clouds/knives-actions.png')

# script = sc.initialize_script('Moonlight')
# generate_tfidf_cloud(script, 'little', False).to_file('clouds/little.png')
# generate_tfidf_cloud(script, 'chiron', False).to_file('clouds/chiron.png')
# generate_tfidf_cloud(script, 'black', False).to_file('clouds/black.png')
# generate_tfidf_cloud(script, None, False).to_file('clouds/moon.png')
# generate_tfidf_cloud(script, None, True).to_file('clouds/moon-actions.png')

# script = sc.initialize_script('The Lord of the Rings: The Fellowship of the Ring')
# generate_tfidf_cloud(script, 'frodo', False).to_file('clouds/frodo.png')
# generate_tfidf_cloud(script, 'gandalf', False).to_file('clouds/gandalf.png')
# generate_tfidf_cloud(script, 'aragorn', False).to_file('clouds/aragorn.png')
# generate_tfidf_cloud(script, None, False).to_file('clouds/lotr.png')
# generate_tfidf_cloud(script, None, True).to_file('clouds/lotr-actions.png')




