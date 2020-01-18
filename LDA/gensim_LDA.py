import sys
import os
import gensim
import gensim.corpora as corpora
from gensim.models import CoherenceModel  # Compute Coherence Score
import pandas as pd
import numpy as np
import tqdm
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.pyplot as plt
from matplotlib import cm

def make_bigrams(texts, bigram_mod):
    return [bigram_mod[doc] for doc in texts]

def create_bow(data):
    # Create Dictionary
    word_dict = corpora.Dictionary(data)  # Create Corpus
    # Term Document Frequency
    corpus = [word_dict.doc2bow(text) for text in data]  # View
    return corpus, word_dict

def compute_coherence_values(corpus, text_data, dictionary, k, a, b):
    """
        Computer the c_v coherence score for an arbitrary LDA model.

        For more info on c_v coherence see:  `M. Röder, A. Both, and A. Hinneburg: Exploring the Space of Topic Coherence Measures. In Proceedings of the eighth International Conference on Web Search and Data Mining, 2015.`

        :param corpus: the text to be modelled (a list of vectors).
        :param text_data: the actual text as a list of list
        :param dictionary: a dictionary coresponding that maps elements of the corpus to words.
        :param k: the number of topics
        :param a: Alpha, document-topic density
        :param b: Beta, topic-word density
    """
    lda_model = gensim.models.LdaMulticore(corpus=corpus,
                                           id2word=dictionary,
                                           num_topics=k,
                                           random_state=100,
                                           chunksize=100,
                                           passes=10,
                                           alpha=a,
                                           eta=b,
                                           per_word_topics=True)
    coherence_model_lda = CoherenceModel(model=lda_model, texts=text_data, dictionary=dictionary, coherence='c_v')
    return coherence_model_lda.get_coherence()

def hyper_parameter_tuning(corpus, word_dict, text_data,min_topics=6,max_topics=11):
    min_topics = min_topics
    max_topics = max_topics
    topics_range = range(min_topics, max_topics)
    # Alpha parameter
    alpha = list(np.arange(0.01, 1, 0.3))
    alpha.append('symmetric')
    alpha.append('asymmetric')
    # Beta parameter
    beta = list(np.arange(0.01, 1, 0.3))
    beta.append('symmetric')
    model_results = {'Topics': [],
                     'Alpha': [],
                     'Beta': [],
                     'Coherence': []
                     }
    num_combinations = len(topics_range)*len(alpha)*len(beta)
    pbar = tqdm.tqdm(total=num_combinations)
    # iterate through number of topics, different alpha values, and different beta values
    for k in topics_range:
        for a in alpha:
            for b in beta:
                # get the coherence score for the given parameters
                cv = compute_coherence_values(
                    corpus=corpus, text_data=text_data, dictionary=word_dict, k=k, a=a, b=b)
                model_results['Topics'].append(k)
                model_results['Alpha'].append(a)
                model_results['Beta'].append(b)
                model_results['Coherence'].append(cv)
                pbar.update(1)
    pbar.close()
    pd.DataFrame(model_results).to_csv('lda_tuning_results.csv', index=False)
    best_val = np.argmax(model_results["Coherence"])
    print("Best c_v val: {} (alpha: {}, beta: {}, topics: {})".format(model_results['Coherence'][best_val],model_results['Alpha'][best_val], model_results['Beta'][best_val],model_results['Topics'][best_val]))
    return model_results['Coherence'][best_val],model_results['Alpha'][best_val], model_results['Beta'][best_val],model_results['Topics'][best_val]

def vis_coherence_surface(file_path,topics=10):
    """
        Visualizes the various hyper-parameters and their coherence score for a set number of topics.
    """
    data = pd.read_csv(file_path)
    data = data[data["Topics"]==topics]
    x = data["Alpha"].apply(lambda x : 0.1 if x=="symmetric" or x=="asymmetric" else x).astype('float64')
    y = data["Beta"].apply(lambda x : 0.1 if x=="symmetric" or x=="asymmetric" else x).astype('float64')
    z = data["Coherence"].astype('float64')
    fig = plt.figure()
    ax = Axes3D(fig)
    # pylint: disable=no-member
    surf = ax.plot_trisurf(x, y, z, cmap=cm.jet, linewidth=0.1)
    fig.colorbar(surf, shrink=0.5, aspect=5)
    ax.set_xlabel('Alpha')
    ax.set_ylabel('Beta')
    ax.set_zlabel('Coherence (c_v)')
    plt.title("Alpha-Beta Hyperparameter Sweep (k={})".format(topics))
    plt.savefig('Coherence_Surface_k={}.png'.format(topics))

def return_hyperparams(corpus,word_dict,text_data,use_existing=True):
    """
        Returns the optimal hyperparameters. Done by sorting saved hyperparams or performing a new hyperparameter sweep.
    """
    to_float = lambda x : x if x=="symmetric" or x=="asymmetric" else float(x)
    exists = os.path.exists("lda_tuning_results.csv")
    params = None
    if not use_existing or not exists:
        print("--- starting hyperparameter tuning ---")
        coherence,alpha,beta,num_topics = hyper_parameter_tuning(corpus, word_dict, text_data)
        return coherence,alpha,beta,num_topics
    params = pd.read_csv("lda_tuning_results.csv")
    params["Alpha"],params["Beta"] = params["Alpha"].apply(to_float),params["Beta"].apply(to_float)
    best_val = params["Coherence"].idxmax()
    return params["Coherence"].loc[best_val],params["Alpha"].loc[best_val],params["Beta"].loc[best_val],params["Topics"].loc[best_val]


def predict(new_doc,lda_model,word_dict):
    try:
        new_doc = new_doc.split()
        BoW = word_dict.doc2bow(new_doc)
        doc_topics, _, _ = lda_model.get_document_topics(BoW, per_word_topics=True)
        return sorted(doc_topics,key=lambda x: x[1], reverse=True)[0][0]
    except:
        # Some rows may have null clean text (example: every token in the tweet is <3 character long). If that's the case return -1 (we want to discard these)
        return -1

if __name__ == "__main__":
    # Put all of the party leaders into one data frame
    usernames = sys.argv[1:]
    frames = []
    for username in usernames:
        file_path = "../data/{}_data.csv".format(username)
        timeline_df = pd.read_csv(file_path)
        print("Number of Tweets for {} is {}".format(username, len(timeline_df)))
        frames.append(timeline_df)
    # The sample(frac=1) shuffles the rows
    text_data = pd.concat(frames,sort=False)["clean_text"].sample(frac=1).values.astype('U')
    text_data = [sent.split() for sent in text_data]
    # Build the bigram models
    print("--- finding bigrams ---")
    bigram = gensim.models.Phrases(text_data, min_count=5, threshold=100)
    bigram_mod = gensim.models.phrases.Phraser(bigram)
    # creates bigrams of words that appear frequently together "gun control" -> "gun_control"
    text_data = make_bigrams(text_data, bigram_mod)
    print("--- creating BoW model ---")
    corpus, word_dict = create_bow(text_data)
    print("--- returning hyperparameters ---")
    # coherence,alpha,beta,num_topics = return_hyperparams(corpus, word_dict, text_data,use_existing=False)
    coherence,alpha,beta,num_topics = return_hyperparams(corpus, word_dict, text_data,use_existing=True)
    # Build LDA model
    print("--- Building model with coherence {:.3f} (Alpha: {}, Beta: {}, Num Topics: {}) ---".format(coherence,alpha,beta,num_topics))
    lda_model = gensim.models.LdaMulticore(corpus=corpus,id2word=word_dict,num_topics=num_topics,alpha=alpha,eta=beta,random_state=100,chunksize=100,passes=10,per_word_topics=True)
    print("--- Updating {} Users Tweet Clusters ---".format(len(usernames)))
    pbar = tqdm.tqdm(total=len(usernames))
    for username in usernames:
        file_path = "../data/{}_data.csv".format(username)
        timeline_df = pd.read_csv(file_path)
        timeline_df["lda_cluster"] = timeline_df["clean_text"].apply(lambda x : predict(x,lda_model,word_dict))
        csvFile = open(file_path, 'w' ,encoding='utf-8')
        timeline_df.to_csv(csvFile, mode='w', index=False, encoding="utf-8")
        pbar.update(1)
    pbar.close()
    for i in range(6,11):
        vis_coherence_surface("lda_tuning_results.csv",topics=i)
    for idx, topic in lda_model.print_topics(-1):
        print('Topic: {} \nWords: {}'.format(idx, topic))
    coherence_model_lda = CoherenceModel(model=lda_model, texts=text_data, dictionary=word_dict, coherence='c_v')
    coherence_lda = coherence_model_lda.get_coherence()
    print('\nCoherence Score: {}'.format(coherence_lda))

