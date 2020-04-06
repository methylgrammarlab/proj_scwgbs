import pickle
import sys

import keras.backend as K
import numpy as np
from sklearn.model_selection import train_test_split

SMALL_SEQ = "seq10"
BIG_SEQ = "sequence"


def load_data_merged(path_to_data, input_len, only_test=False):
    """
    load the data
    :param path_to_data: path to file (consist of train, valid and test data)
    """
    if input_len == 150:
        seq_label = BIG_SEQ
    elif input_len == 10:
        seq_label = SMALL_SEQ
    else:
        raise ("Unknown label to use")

    with open(path_to_data, "rb") as path_to_data_h:
        data = pickle.load(path_to_data_h)

    train_data, test_data = data["train"], data["test"]

    X_test_seq = np.array([seq_to_mat(seq) for seq in test_data[seq_label]])
    y_test = test_data["label"].values

    if only_test:
        return None, None, None, None, X_test_seq, y_test

    X_train_seq = np.array([seq_to_mat(seq) for seq in train_data[seq_label]])
    y_train = train_data["label"].values

    # TODO: in the future need to see how to do it with cross-validation
    X_train_seq, X_valid_seq, y_train, y_valid = train_test_split(X_train_seq, y_train, test_size=0.2,
                                                                  random_state=42)

    return X_train_seq, y_train, X_valid_seq, y_valid, X_test_seq, y_test


########################
### custume metrics ####
########################

def precision(y_true, y_pred):
    true_positives = K.sum(K.round(K.clip(y_true * y_pred, 0, 1)))
    # TPs=K.sum(K.round(K.clip(y_true * y_pred , 0, 1)))
    predicted_positives = K.sum(K.round(K.clip(y_pred, 0, 1)))
    precision = true_positives / (predicted_positives + K.epsilon())
    return precision


def recall(y_true, y_pred):
    true_positives = K.sum(K.round(K.clip(y_true * y_pred, 0, 1)))
    # TPs=K.sum(K.round(K.clip(y_ture * y_pred , 0, 1)))
    possible_positives = K.sum(K.round(K.clip(y_true, 0, 1)))
    recall = true_positives / (possible_positives + K.epsilon())
    return recall


def f1_score(y_true, y_pred):
    precision = precision(y_true, y_pred)
    recall = recall(y_true, y_pred)
    return 2 * ((precision * recall) / (precision + recall + K.epsilon()))


##########################################################
### Function to convert the sequence to one-hot encode ###
##########################################################

def seq_to_mat(seq):
    seq_len = len(seq)
    seq = seq.replace('A', '0')
    seq = seq.replace('a', '0')
    seq = seq.replace('C', '1')
    seq = seq.replace('c', '1')
    seq = seq.replace('G', '2')
    seq = seq.replace('g', '2')
    seq = seq.replace('T', '3')
    seq = seq.replace('t', '3')
    seq = seq.replace('U', '3')
    seq = seq.replace('u', '3')
    seq = seq.replace('N', '4')  # some cases have N in sequence
    seq = seq.replace('n', '4')
    seq_code = np.zeros((4, seq_len), dtype='float16')

    for i in range(seq_len):
        if int(seq[i]) != 4:
            seq_code[int(seq[i]), i] = 1

        else:
            seq_code[0:4, i] = np.tile(0.25, 4)

    return np.transpose(seq_code)


######################################################################################
######### function to find the top k and bottom K frequent 6MERs functions############
######################################################################################

def getkmer(X, y, pred, RBP_index, k):
    from rpy2.robjects.packages import importr
    base = importr('base')
    Biostrings = importr("Biostrings")

    multi_ind_high = [i[0] for i in sorted(enumerate(pred[:, RBP_index]), key=lambda x: x[1], reverse=True) if
                      y[i[0], RBP_index] == 1][0:k]
    multi_ind_low = [i[0] for i in sorted(enumerate(pred[:, RBP_index]), key=lambda x: x[1]) if
                     y[i[0], RBP_index] == 1][0:k]

    multi_fastaseq_low = vecs2dna(np.transpose(X[multi_ind_low], axes=(0, 2, 1)))
    multi_fastaseq_high = vecs2dna(np.transpose(X[multi_ind_high], axes=(0, 2, 1)))

    multi_fastaseq_high = base.unlist(multi_fastaseq_high)
    multi_fastaseq_low = base.unlist(multi_fastaseq_low)
    kmer_freqs_low = base.rowSums(
        base.sapply(Biostrings.DNAStringSet(multi_fastaseq_low),
                    Biostrings.oligonucleotideFrequency, width=6, step=1))
    kmer_freqs_high = base.rowSums(
        base.sapply(Biostrings.DNAStringSet(multi_fastaseq_high),
                    Biostrings.oligonucleotideFrequency, width=6, step=1))

    return kmer_freqs_low, kmer_freqs_high


###############################################################################
######### function to convert one hot encoded sequence to sequence ############
###############################################################################

def vecs2dna(seq_vecs):
    seqs = []

    if len(seq_vecs.shape) == 2:
        seq_vecs = np.reshape(seq_vecs, (seq_vecs.shape[0], 4, -1))
    elif len(seq_vecs.shape) == 4:
        seq_vecs = np.reshape(seq_vecs, (seq_vecs.shape[0], 4, -1))

    for i in range(seq_vecs.shape[0]):
        seq_list = [''] * seq_vecs.shape[2]
        for j in range(seq_vecs.shape[2]):
            if seq_vecs[i, 0, j] == 1:
                seq_list[j] = 'A'
            elif seq_vecs[i, 1, j] == 1:
                seq_list[j] = 'C'
            elif seq_vecs[i, 2, j] == 1:
                seq_list[j] = 'G'
            elif seq_vecs[i, 3, j] == 1:
                seq_list[j] = 'T'
            elif seq_vecs[i, :, j].sum() == 1:
                seq_list[j] = 'N'
            else:
                print('Malformed position vector: ', seq_vecs[i, :, j],
                      'for sequence %d position %d' % (i, j), file=sys.stderr)
        seqs.append(''.join(seq_list))

    return seqs
