import argparse
import json
import numpy as np
import random
import os
import sys

from keras import backend as K
from keras.datasets.cifar import load_batch
from keras.preprocessing import image
from keras.utils import np_utils, data_utils
from keras.utils.data_utils import get_file

import tensorflow as tf

def random_targets(gt, nb_classes):
    """
    Take in the correct labels for each sample and randomly choose target
    labels from the others
    :param gt: the correct labels
    :param nb_classes: The number of classes for this model
    :return: A numpy array holding the randomly-selected target classes
    """
    if len(gt.shape) > 1:
        gt = np.argmax(gt, axis=1)

    result = np.zeros(gt.shape)

    for class_ind in range(nb_classes):
        other_classes = list(range(nb_classes))
        other_classes.remove(class_ind)
        in_cl = gt == class_ind
        result[in_cl] = np.random.choice(other_classes)

    return np_utils.to_categorical(result, nb_classes)

def create_class_pairs(x, y, classes=10, pos=1, neg=0):
    """ Returns a positive and a negative pair per point of x, w.r.t. its class, and their corresponding scores.
    
    :param x: (np.ndarray) sample of points, with M nb of instances as first dimension
    :param y: (np.ndarray) vector of labels, with M nb of instances as first dimension
    :param classes: (int) number of classes
    :param pos: (float) score affected to the positive pairs (couple of similar points)
    :param neg: (float) score attected to the negative pairs (couple of dissimilar points)
    :return: (np.ndarray, np.ndarray) M times classes pairs of points and corresponding scores
    
    """

    pairs = []
    scores = []

    classes_idx = [np.where(y == i)[0] for i in range(classes)]

    for d in range(classes):

        nb = len(classes_idx[d])

        for i in range(nb):

            j = random.randrange(0, nb)
            z1, z2 = classes_idx[d][i], classes_idx[d][j]
            pairs += [[x[z1], x[z2]]]
            scores += [pos]

            dn = (d + random.randrange(1, classes)) % classes
            size = len(classes_idx[dn])
            if size > 0:
                j = random.randrange(0, size)
                z1, z2 = classes_idx[d][i], classes_idx[dn][j]
                pairs += [[x[z1], x[z2]]]

                scores += [neg]

    return np.array(pairs), np.array(scores)


def get_label_conf(y_vec):
    """
    Returns the confidence and the label of the most probable class given a vector of class confidences
    :param y_vec: (np.ndarray) vector of class confidences, nb of intances as first dimension
    :return: (np.ndarray, np.ndarray) confidences and labels
    """
    assert len(y_vec.shape) == 2

    confs, labels = np.amax(y_vec, axis=1), np.argmax(y_vec, axis=1)
    return confs, labels


def get_labels_tf_tensor(preds):
    """
    Returns the label of the most probable class given a tensor of class confidences.
    See get_labels_np_array() for numpy version
    
    :param preds: (tf.tensor) tensor of class confidences, nb of intances as first dimension
    :return: (tf.tensor) labels
    """
    preds_max = tf.reduce_max(preds, 1, keep_dims=True)
    y = tf.to_float(tf.equal(preds, preds_max))
    y /= tf.reduce_sum(y, 1, keep_dims=True)

    return y


def get_labels_np_array(preds):
    """
    Returns the label of the most probable class given a array of class confidences.
    See get_labels_tf_tensor() for tensorflow version

    :param preds: (np.ndarray) array of class confidences, nb of intances as first dimension
    :return: (np.ndarray) labels
    """
    preds_max = np.amax(preds, axis=1, keepdims=True)
    y = (preds == preds_max).astype(float)

    return y


def preprocess(x, y, nb_classes=10, max_value=255):
    """ Scales `x` to [0,1] and converts `y` to class categorical confidences.

    :param x: array of instances
    :param y: array of labels
    :param int nb_classes: 
    :param int max_value: original maximal pixel value
    :return: x,y
    """

    x = x.astype('float32') / max_value
    y = np_utils.to_categorical(y, nb_classes)

    return x, y

# -------------------------------------------------------------------------------------------------------- IO FUNCTIONS

def load_cifar10():
    """Loads CIFAR10 dataset from config.CIFAR10_PATH.

    :return: `(x_train, y_train), (x_test, y_test)`
    :rtype: tuple of numpy.ndarray), (tuple of numpy.ndarray)
    """

    from config import CIFAR10_PATH

    path = data_utils.get_file('cifar-10-batches-py', untar=True, cache_subdir=CIFAR10_PATH,
                               origin='http://www.cs.toronto.edu/~kriz/cifar-10-python.tar.gz')

    num_train_samples = 50000

    x_train = np.zeros((num_train_samples, 3, 32, 32), dtype='uint8')
    y_train = np.zeros((num_train_samples, ), dtype='uint8')

    for i in range(1, 6):
        fpath = os.path.join(path, 'data_batch_' + str(i))
        data, labels = load_batch(fpath)
        x_train[(i - 1) * 10000: i * 10000, :, :, :] = data
        y_train[(i - 1) * 10000: i * 10000] = labels

    fpath = os.path.join(path, 'test_batch')
    x_test, y_test = load_batch(fpath)

    y_train = np.reshape(y_train, (len(y_train), 1))
    y_test = np.reshape(y_test, (len(y_test), 1))

    if K.image_data_format() == 'channels_last':
        x_train = x_train.transpose(0, 2, 3, 1)
        x_test = x_test.transpose(0, 2, 3, 1)

    x_train,y_train = preprocess(x_train,y_train)
    x_test,y_test = preprocess(x_test,y_test)

    return (x_train, y_train), (x_test, y_test)


def load_mnist():

    """Loads MNIST dataset from config.MNIST_PATH
    
    :return: `(x_train, y_train), (x_test, y_test)`
    :rtype: tuple of numpy.ndarray), (tuple of numpy.ndarray)
    """
    from config import MNIST_PATH

    path = data_utils.get_file('mnist.npz', cache_subdir=MNIST_PATH,
                               origin='https://s3.amazonaws.com/img-datasets/mnist.npz')

    f = np.load(path)
    x_train = f['x_train']
    y_train = f['y_train']
    x_test = f['x_test']
    y_test = f['y_test']
    f.close()

    # add channel axis
    x_train = np.expand_dims(x_train, axis=3)
    x_test = np.expand_dims(x_test, axis=3)

    x_train, y_train = preprocess(x_train, y_train)
    x_test, y_test = preprocess(x_test, y_test)

    return (x_train, y_train), (x_test, y_test)

def load_imagenet():

    from config import IMAGENET_PATH

    CLASS_INDEX_PATH = 'https://s3.amazonaws.com/deep-learning-models/image-models/imagenet_class_index.json'

    class_id = IMAGENET_PATH.split("/")[-1]

    fpath = get_file('imagenet_class_index.json', CLASS_INDEX_PATH, cache_subdir='models')
    CLASS_INDEX = json.load(open(fpath))

    for k,v in CLASS_INDEX.items():
        if v[0] == class_id:
            label = k
            break

    dataset = list()

    for root, _, files in os.walk(IMAGENET_PATH):
        for file in files:
            if file.endswith(".jpg"):
                img = image.load_img(os.path.join(root, file), target_size=(224, 224))
                dataset.append(image.img_to_array(img))

    dataset = np.asarray(dataset)
    y = np_utils.to_categorical(np.asarray([label]*len(dataset)), 1000)

    try:
        x_train, x_test = dataset[:700], dataset[700:]
        y_train, y_test = y[:700], y[700:]
    except:
        x_train, x_test = dataset[:2], dataset[0:]
        y_train, y_test = y[:2], y[0:]

    return (x_train, y_train), (x_test, y_test)

def load_dataset(name):
    """
    Loads the original dataset corresponding to name.
    :param name: (str) name or path of the dataset
    :return: `(x_train, y_train), (x_test, y_test)`
    """

    if "mnist" in name:
        return load_mnist()

    elif "cifar10" in name:
        return load_cifar10()

    elif "imagenet" in name:
        return load_imagenet()

    else:
        raise NotImplementedError("There is no loader for {} dataset".format(name))

def make_directory(dir_path):
    """
    Creates the specified tree of directories if needed.
    :param dir_path: (str) directory or file path
    :return: None
    """
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)


def get_npy_files(path):
    """
    generator
    Returns all the npy files in path subdirectories.
    :param path: (str) directory path
    :return: (str) paths
    """

    for root, _, files in os.walk(path):
        for file in files:
            if file.endswith(".npy"):
                yield os.path.join(root, file)

def set_group_permissions_rec(path, group="drl-dwl"):
    for root, _, files in os.walk(path):
        set_group_permissions(root, group)

        for f in files:
            try:
                set_group_permissions(os.path.join(root, f), group)
            except:
                pass


def set_group_permissions(filename, group="drl-dwl"):
    import shutil
    shutil.chown(filename, user=None, group=group)

    os.chmod(filename, 0o774)

# ------------------------------------------------------------------- ARG PARSER

def get_args(prog, load_classifier=False, load_sample=False, per_batch=False, options=""):

    parser = argparse.ArgumentParser(prog=prog, formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    option_dict = {
        "a": {"flags": ["-a", "--adv"],
              "kwargs": {"type":str, "dest":'adv_method', "default": "fgsm",
                         "choices":["fgsm", "deepfool", "universal"], "help":'choice of attacker'}},
        "b": {"flags": ["-b", "--batchsize"],
              "kwargs": {"type": int, "dest": 'batch_size', "default": 128, "help": 'size of the batches'}},
        "c": {"flags" : ["-c", "--classifier"],
              "kwargs": { "type":str, "dest":'classifier', "default":"cnn", "choices": ["cnn", "resnet"],
                          "help":'choice of classifier'}},
        "d": {"flags": ["-d", "--dataset"],
              "kwargs": {"type":str, "dest":'dataset', "default":"mnist",
                        "help":'either the path or name of the dataset the classifier is tested/trained on.'}},
        "e": {"flags": ["-e", "--epochs"],
              "kwargs": {"type": int, "dest": 'nb_epochs', "default": 20,
                                                      "help": 'number of epochs for training the classifier'}},
        "f": {"flags": ["-f", "--act"],
              "kwargs": {"type": str, "dest": 'act', "default": "relu", "choices": ["relu", "brelu"],
                         "help": 'choice of activation function'}},
        "n": {"flags": ["-n", "--nbinstances"],
              "kwargs": {"type": int, "dest": 'nb_instances', "default": 1,
                         "help": 'number of supplementary instances per true example'}},
        "r": {"flags": ["-r", "--valsplit"],
              "kwargs": {"type":float, "dest":'val_split', "default": 0.1,
                                                        "help":'ratio of training sample used for validation'}},
        "s": {"flags": ["-s", "--save"],
              "kwargs": {"nargs":'?', "type":str, "dest":'save', "default": False,
                                                    "help":'if set, the classifier is saved; if an argument is provided'
                                                    'it is used as path to store the model '}},
        "t": {"flags": ["-t", "--stdev"],
              "kwargs": {"type":float, "dest":'std_dev', "default": 0.1,
                                                     "help":'standard deviation of the distributions'}},
        "v": {"flags": ["-v", "--verbose"],
              "kwargs": {"dest":'verbose', "action":"store_true", "help":'if set, verbose mode'}},
        "z": {"flags": ["-z", "--defences"],
              "kwargs": {"dest":'defences', "nargs":"*", "default": None, "help":'list of basic defences.'}},
    }

    # add required arguments
    if load_classifier:
        parser.add_argument("load", type=str, help='the classifier is loaded from `load` directory.')

    if load_sample:
        parser.add_argument("adv_path", type=str, help='path to the dataset for data augmentation training.')

    if per_batch:
        parser.add_argument("batch_idx", type=int, help='index of the batch to use.')

    # add optional arguments
    for o in options:
        parser.add_argument(*option_dict[o]["flags"], **option_dict[o]["kwargs"])

    return parser.parse_args()

def get_verbose_print(verbose):
    """
    Sets verbose mode.
    :param verbose: (bool) True for verbose, False for quiet
    :return: (function) printing function
    """
    if verbose:
        return print
    else:
        return lambda *a, **k: None
