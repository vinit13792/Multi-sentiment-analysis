# -*- coding: utf-8 -*-
"""Final Notebook.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1441TTlaTX6ZMeIWwBJstFVASNYmO2D_U
"""
from google_drive_downloader import GoogleDriveDownloader as gdd
import nltk
from nltk.tokenize import word_tokenize, sent_tokenize
nltk.download('stopwords')
import zipfile
nltk.download('punkt')
nltk.download('averaged_perceptron_tagger')
nltk.download('wordnet')
from nltk.corpus import stopwords
import spacy
from spacy import displacy

import streamlit as st
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.linear_model import LogisticRegression, SGDClassifier
from sklearn.model_selection import RandomizedSearchCV
from xgboost import XGBClassifier
from collections import defaultdict, Counter
from sklearn.svm import SVC
from sklearn.calibration import CalibratedClassifierCV
from tensorflow.keras.preprocessing.sequence import pad_sequences
import pandas as pd
import numpy as np
from prettytable import PrettyTable
import itertools
from sklearn.preprocessing import Normalizer
import pickle
import string
import re
import joblib
import os
import glob
    
stop_words = set(stopwords.words('english'))

gdd.download_file_from_google_drive(file_id='1aQ7Ns6DYhq3MKSoeQEG3gl7OLKgtRT44',
                                    dest_path='/app/multi-sentiment-analysis/greet models.zip',
                                    unzip=True)
gdd.download_file_from_google_drive(file_id='1Lz-bjuFshJY8LiXFgKpTZodqJqq6IYGX',
                                    dest_path='/app/multi-sentiment-analysis/backstory models.zip',
                                    unzip=True)
gdd.download_file_from_google_drive(file_id='1rja_wtez5BrfowiXIP91mveDAukMJTjH',
                                    dest_path='/app/multi-sentiment-analysis/justifn models.zip',
                                    unzip=True)
gdd.download_file_from_google_drive(file_id='1bijUPhMKDCFzkKnm2udVl9IFtcEyfuc-',
                                    dest_path='/app/multi-sentiment-analysis/rant models.zip',
                                    unzip=True)
gdd.download_file_from_google_drive(file_id='19iQ0Weweam2gT5_9P8G6rry6U6fjYpSf',
                                    dest_path='/app/multi-sentiment-analysis/grat models.zip',
                                    unzip=True)
gdd.download_file_from_google_drive(file_id='1IVi2cGx66iXuyx-Q8UzdW55VtSf-E-ul',
                                    dest_path='/app/multi-sentiment-analysis/other models.zip',
                                    unzip=True)
gdd.download_file_from_google_drive(file_id='1pWLS_D8qPkbGHVL7TI0h_KNiVCjTKgdJ',
                                    dest_path='/app/multi-sentiment-analysis/expemo models.zip',
                                    unzip=True)
gdd.download_file_from_google_drive(file_id='1bY96HSWMuatJ8cprhWHVcTzUSK8farhh',
                                    dest_path='/app/multi-sentiment-analysis/unigram_feat_multi.pkl',
                                    unzip=False) # unigram dictionary
gdd.download_file_from_google_drive(file_id='1nZk37wAd4BfUCNrLaquKpfsrXnWLG-Fu',
                                    dest_path='/app/multi-sentiment-analysis/norm_trans.sav',
                                    unzip=False) # normaliser fitted on training data 


# All files ending with .txt
zipfiles = glob.glob("/app/multi-sentiment-analysis/*.zip")
#st.write(zipfiles)
for file in zipfiles:
    with zipfile.ZipFile(f'{file}', 'r') as zip_ref:
        zip_ref.extractall()                       

#for file in os.listdir(os.getcwd()):
#    st.write(file)
@st.cache
def decontracted(phrase):
    # specific
    phrase = re.sub(r"won't", "will not", phrase)
    phrase = re.sub(r"can\'t", "can not", phrase)

    # general
    phrase = re.sub(r"n\'t", " not", phrase)
    phrase = re.sub(r"\'re", " are", phrase)
    phrase = re.sub(r"\'s", " is", phrase)
    phrase = re.sub(r"\'d", " would", phrase)
    phrase = re.sub(r"\'ll", " will", phrase)
    phrase = re.sub(r"\'t", " not", phrase)
    phrase = re.sub(r"\'ve", " have", phrase)
    phrase = re.sub(r"\'m", " am", phrase)
    return phrase

@st.cache
def Find(string):
  
    # findall() has been used 
    # with valid conditions for urls in string
    regex = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
    url = re.findall(regex,string) 
    temp = ''
    for x in url:
      temp+=''.join(x[0])
    return temp

@st.cache
def clean_text(df, feature):
    
    cleaned_text = []
    
    for i in range(df.shape[0]):
        
        doc = df[feature].values[i]
        
        url = Find(doc)
        
        doc = re.sub(url, '', doc)
        
        doc = re.findall(r'\w+', doc)
        
        table = str.maketrans('', '', string.punctuation)
        
        stripped = [w.translate(table) for w in doc]
        
        doc = ' '.join(stripped)
        
        doc = doc.lower()

        # remove text followed by numbers
        doc = re.sub('[^A-Za-z0-9]+', ' ', doc)

        # remove text which appears inside < > or text preceeding or suceeding <, >
        doc = re.sub(r'< >|<.*?>|<>|\>|\<', ' ', doc)

        # remove anything inside brackets
        doc = re.sub(r'\(.*?\)', ' ', doc)
        
        # remove digits
        doc = re.sub(r'\d+', ' ', doc)
        cleaned_text.append(doc)
        
    return cleaned_text


@st.cache
def get_word_count(data, feature):
    
    counts = []
    
    for i in range(data[feature].shape[0]):
        
        text = data[feature].values[i]
        pattern = r'[a-zA-Z]+'
        
        words = re.findall(pattern, text)
        
        counts.append(len(words))
        
    return counts

@st.cache
def pos_count(data, feature):

  POS_List = ['JJ', 'JJR', 'JJS', 'NN', 'NNS', 'PRP', 'PRPS', 'RB', 'RBR', 'RP', 'UH', 'VB', 'VBD', 'VBG', 'VBN', 'VBP','VBZ', 'WP', 'WP$']
  
  pos_per_text = defaultdict(list)

  for i in range(data.shape[0]):

    doc = data['Text'].values[i]

    info =[]
    tokenized = sent_tokenize(doc)
    for i in tokenized:

      # Word tokenizers is used to find the words 
      # and punctuation in a string
      wordsList = nltk.word_tokenize(i)
  
      # removing stop words from wordList
      wordsList = [w for w in wordsList if not w in stop_words] 
  
      #  Using a Tagger. Which is part-of-speech 
      # tagger or POS-tagger. 
      tagged = nltk.pos_tag(wordsList)
    
      for tag in tagged:
        info.append(tag[1])
    #print(info)
    
    
    counts = Counter(info)
    
    keys = dict(counts).keys()
    #print(list(keys))
    #break
    for pos in POS_List:
      
      if pos in list(keys):
        
        pos_per_text[pos].append(counts.get(pos))
            
      else:
        pos_per_text[pos].append(0)
      
  return pos_per_text


@st.cache
def check_negation(df):
    
    negex_ = []
    
    for i in range(df.shape[0]):
        sent = df['Text'].values[i].split()
        if ('not' in sent) or ('never' in sent):
            negex_.append(1)
        else:
            negex_.append(0)
    return negex_

@st.cache
def get_pos_vec(df, feature):
  ci = ['CC', 'DT', 'EX', 'IN', 'MD', 'PDT', 'POS', 'RB', 'RBR', 'RBS', 'RP', 'TO', 'WDT', 'WP', 'WP$', 'WRB']
  gfi = ['CD', 'FW', 'LS', 'NNP', 'NNPS', 'PRP', 'PRP$', 'SYM', 'UH']
  ei = ['JJ', 'JJR','JJS','NN','NNS','VB','VBD','VBD','VBG','VBN','VBP','VBZ']
  pos_cat = defaultdict(list)
  
  for i in range(df.shape[0]):

    doc = df[feature].values[i]
    pattern =[]
    tokenized = sent_tokenize(doc)
    for i in tokenized:

      # Word tokenizers is used to find the words 
      # and punctuation in a string
      wordsList = nltk.word_tokenize(i)
  
      # removing stop words from wordList
      wordsList = [w for w in wordsList if not w in stop_words] 
  
      #  Using a Tagger. Which is part-of-speech 
      # tagger or POS-tagger. 
      tagged = nltk.pos_tag(wordsList)

      
      for tag in tagged:
        pattern.append(tag[1]) 
    
    
    pat_check_ci = [pat for pat in pattern if pat in ci]
    pat_check_ei = [pat for pat in pattern if pat in ei]
    pat_check_gfi = [pat for pat in pattern if pat in gfi]
    #print('-----')
    #print(pat_check_ci, 'ci')
    #print(pat_check_gfi, 'gfi')
    #print(pat_check_ei, 'ei')
    
    if (len(pat_check_ci)!=0) and (len(pat_check_ei)!=0) and (len(pat_check_gfi)!=0):
      pos_cat['CI'].append(1)
      pos_cat['EI'].append(1)
      pos_cat['GFI'].append(1)
    elif (len(pat_check_ci)==0) and (len(pat_check_ei)!=0) and (len(pat_check_gfi)!=0):
      pos_cat['CI'].append(0)
      pos_cat['EI'].append(1)
      pos_cat['GFI'].append(1)
    elif (len(pat_check_ci)!=0) and (len(pat_check_ei)==0) and (len(pat_check_gfi)!=0):
      pos_cat['CI'].append(1)
      pos_cat['EI'].append(0)
      pos_cat['GFI'].append(1)
    elif (len(pat_check_ci)!=0) and (len(pat_check_ei)!=0) and (len(pat_check_gfi)==0):
      pos_cat['CI'].append(1)
      pos_cat['EI'].append(1)
      pos_cat['GFI'].append(0)
    elif (len(pat_check_ci)!=0) and (len(pat_check_ei)==0) and (len(pat_check_gfi)==0):
      pos_cat['CI'].append(1)
      pos_cat['EI'].append(0)
      pos_cat['GFI'].append(0)
    elif (len(pat_check_ci)==0) and (len(pat_check_ei)==0) and (len(pat_check_gfi)!=0):
      pos_cat['CI'].append(0)
      pos_cat['EI'].append(0)
      pos_cat['GFI'].append(1)
    else:
      pos_cat['CI'].append(0)
      pos_cat['EI'].append(1)
      pos_cat['GFI'].append(0)

  return pos_cat

unigram_feat_multi = pickle.load(open('/app/multi-sentiment-analysis/unigram_feat_multi.pkl', 'rb'))

@st.cache
def text_to_seq(vocab, data):

  sequences = []
  for i in range(data.shape[0]):
    text = re.findall(r'[a-zA-Z]+|\~|\!|\@|\#|\$|\%|\^|\&|\*|\(|\)|\-\+|\,|\"|\?|\.|\:|\;|\=|\[|\]|\{|\}|\_|\\|\/', data['Text'].values[i])
    seq = []
    for i in text:
      if vocab.get(i)==None:
        seq.append(1)
      else:
        seq.append(vocab.get(i))
    sequences.append(seq)

  return np.array(sequences)

normaliser = joblib.load('/app/multi-sentiment-analysis/norm_trans.sav')

@st.cache
def predict(X):

  #greet_cat = joblib.load('content/greet models/calib_catd1_greet.sav')
  #greet_rf = joblib.load('content/greet models/calib_d1_greetrf.sav')
  greet_xgb = joblib.load('/app/multi-sentiment-analysis/greet models/calib_d1xgb_greet.sav')
  #greet_dtc = joblib.load('content/greet models/calib_dtc_greet.sav')
  greet_sgd = joblib.load('/app/multi-sentiment-analysis/greet models/calib_sgdd1_greet.sav')
  greet_lr = joblib.load('/app/multi-sentiment-analysis/greet models/calib_lr_d1_greet.sav')
  greet_gnb = joblib.load('/app/multi-sentiment-analysis/greet models/calib_gnb_d1_greet.sav')
  greet_meta = joblib.load('/app/multi-sentiment-analysis/greet models/calib_meta_lrgreet.sav')

  #greet_cat_pred = greet_cat.predict_proba(X)[:,1]
  #greet_rf_pred = greet_rf.predict_proba(X)[:,1]
  greet_xgb_pred = greet_xgb.predict_proba(X)[:,1]
  #greet_dtc_pred = greet_dtc.predict_proba(X)[:,1]
  greet_sgd_pred = greet_sgd.predict_proba(X)[:,1]
  greet_lr_pred = greet_lr.predict_proba(X)[:,1]
  greet_gnb_pred = greet_gnb.predict_proba(X)[:,1]

  greet_meta_array = np.hstack((#greet_rf_pred.reshape(-1,1),   greet_dtc_pred.reshape(-1,1), 
                            greet_xgb_pred.reshape(-1,1),  greet_sgd_pred.reshape(-1,1), 
                          greet_lr_pred.reshape(-1,1), greet_gnb_pred.reshape(-1,1))) #greet_cat_pred.reshape(-1,1), 
  
  greet_meta_preds = np.round(greet_meta.predict_proba(greet_meta_array)[:,1],2)

  #back_cat = joblib.load('content/backstory models/calib_catd1_back.sav')
  #back_rf = joblib.load('content/backstory models/calib_d1_backrf.sav')
  back_xgb = joblib.load('/app/multi-sentiment-analysis/backstory models/calib_d1xgb_back.sav')
  #back_dtc = joblib.load('content/backstory models/calib_dtc_back.sav')
  back_sgd = joblib.load('/app/multi-sentiment-analysis/backstory models/calib_sgdd1_back.sav')
  back_lr = joblib.load('/app/multi-sentiment-analysis/backstory models/calib_lr_d1_back.sav')
  back_gnb = joblib.load('/app/multi-sentiment-analysis/backstory models/calib_gnb_d1_back.sav')
  back_meta = joblib.load('/app/multi-sentiment-analysis/backstory models/calib_meta2_lrback.sav')

  #back_cat_pred = back_cat.predict_proba(X)[:,1]
  #back_rf_pred = back_rf.predict_proba(X)[:,1]
  back_xgb_pred = back_xgb.predict_proba(X)[:,1]
  #back_dtc_pred = back_dtc.predict_proba(X)[:,1]
  back_sgd_pred = back_sgd.predict_proba(X)[:,1]
  back_lr_pred = back_lr.predict_proba(X)[:,1]
  back_gnb_pred = back_gnb.predict_proba(X)[:,1]

  back_meta_array = np.hstack((#back_rf_pred.reshape(-1,1), #back_dtc_pred.reshape(-1,1), 
                               back_xgb_pred.reshape(-1,1),back_sgd_pred.reshape(-1,1), 
                          back_lr_pred.reshape(-1,1), back_gnb_pred.reshape(-1,1))) #back_cat_pred.reshape(-1,1), 
  
  back_meta_preds = np.round(back_meta.predict_proba(back_meta_array)[:,1],2)

  #justifn_cat = joblib.load('content/justifn models/calib_catd1_justifn.sav')
  #justifn_rf = joblib.load('content/justifn models/calib_d1_justifnrf.sav')
  justifn_xgb = joblib.load('/app/multi-sentiment-analysis/justifn models/calib_d1xgb_justifn.sav')
  #justifn_dtc = joblib.load('content/justifn models/calib_dtc_justifn.sav')
  justifn_sgd = joblib.load('/app/multi-sentiment-analysis/justifn models/calib_sgdd1_justifn.sav')
  justifn_lr = joblib.load('/app/multi-sentiment-analysis/justifn models/calib_lr_d1_justifn.sav')
  justifn_gnb = joblib.load('/app/multi-sentiment-analysis/justifn models/calib_gnb_d1_justifn.sav')
  justifn_meta = joblib.load('/app/multi-sentiment-analysis/justifn models/calib_meta2_lrjustifn.sav')

  #justifn_cat_pred = justifn_cat.predict_proba(X)[:,1]
  #justifn_rf_pred = justifn_rf.predict_proba(X)[:,1]
  justifn_xgb_pred = justifn_xgb.predict_proba(X)[:,1]
  #justifn_dtc_pred = justifn_dtc.predict_proba(X)[:,1]
  justifn_sgd_pred = justifn_sgd.predict_proba(X)[:,1]
  justifn_lr_pred = justifn_lr.predict_proba(X)[:,1]
  justifn_gnb_pred = justifn_gnb.predict_proba(X)[:,1]

  justifn_meta_array = np.hstack((#justifn_rf_pred.reshape(-1,1),  justifn_dtc_pred.reshape(-1,1),#
                                 justifn_xgb_pred.reshape(-1,1), justifn_sgd_pred.reshape(-1,1),  #justifn_cat_pred.reshape(-1,1), 
                          justifn_lr_pred.reshape(-1,1), justifn_gnb_pred.reshape(-1,1)))
  
  justifn_meta_preds = np.round(justifn_meta.predict_proba(justifn_meta_array)[:,1],2)

  
  #rant_cat = joblib.load('content/rant models/calib_catd1_rant.sav')
  #rant_rf = joblib.load('content/rant models/calib_d1_rantrf.sav')
  rant_xgb = joblib.load('/app/multi-sentiment-analysis/rant models/calib_d1xgb_rant.sav')
  #rant_dtc = joblib.load('content/rant models/calib_dtc_rant.sav')
  rant_sgd = joblib.load('/app/multi-sentiment-analysis/rant models/calib_sgdd1_rant.sav')
  rant_lr = joblib.load('/app/multi-sentiment-analysis/rant models/calib_lr_d1_rant.sav')
  rant_gnb = joblib.load('/app/multi-sentiment-analysis/rant models/calib_gnb_d1_rant.sav')
  rant_meta = joblib.load('/app/multi-sentiment-analysis/rant models/calib_meta2_lrrant.sav')

  #rant_cat_pred = rant_cat.predict_proba(X)[:,1]
  #rant_rf_pred = rant_rf.predict_proba(X)[:,1]
  rant_xgb_pred = rant_xgb.predict_proba(X)[:,1]
  #rant_dtc_pred = rant_dtc.predict_proba(X)[:,1]
  rant_sgd_pred = rant_sgd.predict_proba(X)[:,1]
  rant_lr_pred = rant_lr.predict_proba(X)[:,1]
  rant_gnb_pred = rant_gnb.predict_proba(X)[:,1]

  rant_meta_array = np.hstack((#rant_rf_pred.reshape(-1,1), #rant_dtc_pred.reshape(-1,1),  #rant_cat_pred.reshape(-1,1), 
                               rant_xgb_pred.reshape(-1,1), rant_sgd_pred.reshape(-1,1), 
                          rant_lr_pred.reshape(-1,1), rant_gnb_pred.reshape(-1,1)))
  
  rant_meta_preds = np.round(rant_meta.predict_proba(rant_meta_array)[:,1],2)

  
  #other_cat = joblib.load('content/other models/calib_catd1_other.sav')
  #other_rf = joblib.load('content/other models/calib_d1_otherrf.sav')
  other_xgb = joblib.load('/app/multi-sentiment-analysis/other models/calib_d1xgb_other.sav')
  #other_dtc = joblib.load('content/other models/calib_dtc_other.sav')
  other_sgd = joblib.load('/app/multi-sentiment-analysis/other models/calib_sgdd1_other.sav')
  other_lr = joblib.load('/app/multi-sentiment-analysis/other models/calib_lr_d1_other.sav')
  other_gnb = joblib.load('/app/multi-sentiment-analysis/other models/calib_gnb_d1_other.sav')
  other_meta = joblib.load('/app/multi-sentiment-analysis/other models/calib_meta2_lrother.sav')

  #other_cat_pred = other_cat.predict_proba(X)[:,1]
  #other_rf_pred = other_rf.predict_proba(X)[:,1]
  other_xgb_pred = other_xgb.predict_proba(X)[:,1]
  #other_dtc_pred = other_dtc.predict_proba(X)[:,1]
  other_sgd_pred = other_sgd.predict_proba(X)[:,1]
  other_lr_pred = other_lr.predict_proba(X)[:,1]
  other_gnb_pred = other_gnb.predict_proba(X)[:,1]

  other_meta_array = np.hstack((#other_rf_pred.reshape(-1,1), #
                                other_xgb_pred.reshape(-1,1), other_sgd_pred.reshape(-1,1), 
                          other_lr_pred.reshape(-1,1), other_gnb_pred.reshape(-1,1))) #other_cat_pred.reshape(-1,1), 
  
  other_meta_preds = np.round(other_meta.predict_proba(other_meta_array)[:,1],2)

  
  #expemo_cat = joblib.load('content/expemo models/calib_catd1_expemo.sav')
  #expemo_rf = joblib.load('content/expemo models/calib_d1_expemorf.sav')
  expemo_xgb = joblib.load('/app/multi-sentiment-analysis/expemo models/calib_d1xgb_expemo.sav')
  #expemo_dtc = joblib.load('content/expemo models/calib_dtc_expemo.sav')
  expemo_sgd = joblib.load('/app/multi-sentiment-analysis/expemo models/calib_sgdd1_expemo.sav')
  expemo_lr = joblib.load('/app/multi-sentiment-analysis/expemo models/calib_lr_d1_expemo.sav')
  expemo_gnb = joblib.load('/app/multi-sentiment-analysis/expemo models/calib_gnb_d1_expemo.sav')
  expemo_meta = joblib.load('/app/multi-sentiment-analysis/expemo models/calib_meta2_lrexpemo.sav')

  #expemo_cat_pred = expemo_cat.predict_proba(X)[:,1]
  #expemo_rf_pred = expemo_rf.predict_proba(X)[:,1]
  expemo_xgb_pred = expemo_xgb.predict_proba(X)[:,1]
  #expemo_dtc_pred = expemo_dtc.predict_proba(X)[:,1]
  expemo_sgd_pred = expemo_sgd.predict_proba(X)[:,1]
  expemo_lr_pred = expemo_lr.predict_proba(X)[:,1]
  expemo_gnb_pred = expemo_gnb.predict_proba(X)[:,1]

  expemo_meta_array = np.hstack((#expemo_dtc_pred.reshape(-1,1),expemo_rf_pred.reshape(-1,1), #
                                 expemo_xgb_pred.reshape(-1,1), expemo_sgd_pred.reshape(-1,1), 
                          expemo_lr_pred.reshape(-1,1), expemo_gnb_pred.reshape(-1,1)))  #expemo_cat_pred.reshape(-1,1), 
  
  expemo_meta_preds = np.round(expemo_meta.predict_proba(expemo_meta_array)[:,1],2)

  return greet_meta_preds[0]*100, back_meta_preds[0]*100, justifn_meta_preds[0]*100, rant_meta_preds[0]*100, other_meta_preds[0]*100, expemo_meta_preds[0]*100

@st.cache
def preprocess(X):

  POS_List = ['JJ', 'JJR', 'JJS', 'NN', 'NNS', 'PRP', 'PRPS', 'RB', 'RBR', 'RP', 'UH', 'VB', 'VBD', 'VBG', 'VBN', 'VBP','VBZ', 'WP', 'WP$']

  df = pd.DataFrame(data={X}, columns=['Text'])
  df['Text'].values[0] = decontracted(df['Text'].values[0])
  df['Clean Text'] = clean_text(df, 'Text')
  df['word_count'] = get_word_count(df, 'Text')
  parts_of_speech_counts = pos_count(df, 'Text')

  for pos in POS_List:
    df[pos] = parts_of_speech_counts.get(pos)

  df['Negation'] = check_negation(df)

  pos_cat = get_pos_vec(df, 'Text')
  df['CI'] = pos_cat.get('CI')
  df['GFI'] = pos_cat.get('GFI')
  df['EI'] = pos_cat.get('EI')
  
  unigram_feat_multi = pickle.load(open('/app/multi-sentiment-analysis/unigram_feat_multi.pkl', 'rb'))
  puncs = [i for i in string.punctuation]
  unigram_feat_multi = puncs + list(unigram_feat_multi)
  dictionary_multi = list(unigram_feat_multi)

  word_index_multi= dict()

  for i in range(len(dictionary_multi)):
      if i==0:
        word_index_multi['OOV'] = 1
      else:
        word_index_multi[dictionary_multi[i]]=i+1
  # Based on max length of sentences in training data
  maxlen = 264

  text_array = text_to_seq(word_index_multi, df)
  text_array = pad_sequences(text_array, maxlen=maxlen, dtype='int32', padding='pre',truncating='post')
  df.drop('Clean Text', axis=1, inplace=True)
  keep_columns = list(df.columns[1:])
  data_cols = df[keep_columns].values

  query = np.hstack((text_array, data_cols))
  query = normaliser.transform(query)
  
  greet, back, justifn, rant, other, expemo =  predict(query)
  return greet, back, justifn, rant, other, expemo

st.title('Multi-sentiment Analysis and Prediction on TripAdvisor data.')
st.markdown('This project involves sentiment analysis and prediction of multiple sentiments. It is an implementation of [this](https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber=8496747) Sep 2019 paper by MONDHER BOUAZIZI AND TOMOAKI OHTSUKI', unsafe_allow_html=True)
st.markdown('The authors acheived 60.2% overall accuracy on the twitter data, which is phenomenal considering that twitter has limited number of words and extracting meaning out of those words becomes quite tedious as the person who tweets often has multiple layers of message wrapped in a limited words. ')
st.markdown('The main purpose of this project is to showcase that even though the techniques used by the author involved predictions on twitter data, the same techniques can be used in travel industry to identify the sentiments carried by the customers who post on the travel forums, regarding their ticket bookings, or flight plans. Customers often post a query and wait eagerly for a reply by the travel agency rep. We can use this to post a response taking in consideration the emotion a customer has and respond until a rep gets in touch with them. This way a customer wont have to wait longer.') 

X = st.text_input(label='Enter your text here')

greet, back, justifn, rant, other, expemo = preprocess(X)

st.write('Greeting: ', greet,' %')
st.write('Backstory: ', back,' %')
st.write('Justification:',justifn,' %')
st.write('Rant: ',rant,' %')
st.write('Other: ',other,' %')
st.write('Express Emotion: ', expemo, ' %')
