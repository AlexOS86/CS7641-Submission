import copy
import logging
import pandas as pd
import numpy as np

from collections import Counter

from sklearn import preprocessing, utils
import sklearn.model_selection as ms
from scipy.sparse import isspmatrix
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


import os
import seaborn as sns

from abc import ABC, abstractmethod

# TODO: Move this to a common lib? That way all of the assignments go to the same output
OUTPUT_DIRECTORY = './output'


# this checks if the directory already exists. If it not it makes it
if not os.path.exists(OUTPUT_DIRECTORY):
    os.makedirs(OUTPUT_DIRECTORY)
if not os.path.exists('{}/images'.format(OUTPUT_DIRECTORY)):
    os.makedirs('{}/images'.format(OUTPUT_DIRECTORY))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def plot_pairplot(title, df, class_column_name=None):
    plt = sns.pairplot(df, hue=class_column_name)
    return plt


# Adapted from https://stats.stackexchange.com/questions/239973/a-general-measure-of-data-set-imbalance
# the balanced uses to determine if the F1 if not balanced and accuracy scorer if it is balanced
def is_balanced(seq):
    n = len(seq)
    classes = [(clas, float(count)) for clas, count in Counter(seq).items()]
    k = len(classes)

    H = -sum([(count/n) * np.log((count/n)) for clas, count in classes])
    return H/np.log(k) > 0.75

# extends the abstract class to create new loader class
class DataLoader(ABC):
    def __init__(self, path, verbose, seed):
        self._path = path
        self._verbose = verbose
        self._seed = seed

        self.features = None
        self.classes = None
        self.testing_x = None
        self.testing_y = None
        self.training_x = None
        self.training_y = None
        self.binary = False
        self.balanced = False
        self._data = pd.DataFrame()

    def load_and_process(self, data=None, preprocess=True):
        """
        Load data from the given path and perform any initial processing required. This will populate the
        features and classes and should be called before any processing is done.

        :return: Nothing
        """
        if data is not None:
            self._data = data
            self.features = None
            self.classes = None
            self.testing_x = None
            self.testing_y = None
            self.training_x = None
            self.training_y = None
        else:
            self._load_data()
        self.log("Processing {} Path: {}, Dimensions: {}", self.data_name(), self._path, self._data.shape)
        if self._verbose:
            old_max_rows = pd.options.display.max_rows
            pd.options.display.max_rows = 10
            self.log("Data Sample:\n{}", self._data)
            pd.options.display.max_rows = old_max_rows

        if preprocess:
            self.log("Will pre-process data")
            self._preprocess_data()

        self.get_features()
        self.get_classes()
        self.log("Feature dimensions: {}", self.features.shape)
        self.log("Classes dimensions: {}", self.classes.shape)
        self.log("Class values: {}", np.unique(self.classes))
        class_dist = np.histogram(self.classes)[0]
        class_dist = class_dist[np.nonzero(class_dist)]
        self.log("Class distribution: {}", class_dist)
        self.log("Class distribution (%): {}", (class_dist / self.classes.shape[0]) * 100)
        self.log("Sparse? {}", isspmatrix(self.features))

        if len(class_dist) == 2:
            self.binary = True
        self.balanced = is_balanced(self.classes)

        self.log("Binary? {}", self.binary)
        self.log("Balanced? {}", self.balanced)



    def scale_standard(self):
        self.features = StandardScaler().fit_transform(self.features)
        if self.training_x is not None:
            self.training_x = StandardScaler().fit_transform(self.training_x)

        if self.testing_x is not None:
            self.testing_x = StandardScaler().fit_transform(self.testing_x)

    def build_train_test_split(self, test_size=0.3):
        if not self.training_x and not self.training_y and not self.testing_x and not self.testing_y:
            self.training_x, self.testing_x, self.training_y, self.testing_y = ms.train_test_split(
                self.features, self.classes, test_size=test_size, random_state=self._seed, stratify=self.classes
            )

    def get_features(self, force=False):
        if self.features is None or force:
            self.log("Pulling features")
            self.features = np.array(self._data.iloc[:, 0:-1])

        return self.features

    def get_classes(self, force=False):
        if self.classes is None or force:
            self.log("Pulling classes")
            self.classes = np.array(self._data.iloc[:, -1])

        return self.classes

    #tis sets up the nitial test and train size and sets the radom set so that
    def dump_test_train_val(self, test_size=0.2, random_state=123):
        ds_train_x, ds_test_x, ds_train_y, ds_test_y = ms.train_test_split(self.features, self.classes,
                                                                           test_size=test_size,
                                                                           random_state=random_state,
                                                                           stratify=self.classes)
        pipe = Pipeline([('Scale', preprocessing.StandardScaler())])
        train_x = pipe.fit_transform(ds_train_x, ds_train_y)
        train_y = np.atleast_2d(ds_train_y).T
        test_x = pipe.transform(ds_test_x)
        test_y = np.atleast_2d(ds_test_y).T

        train_x, validate_x, train_y, validate_y = ms.train_test_split(train_x, train_y,
                                                                       test_size=test_size, random_state=random_state,
                                                                       stratify=train_y)
        test_y = pd.DataFrame(np.where(test_y == 0, -1, 1))
        train_y = pd.DataFrame(np.where(train_y == 0, -1, 1))
        validate_y = pd.DataFrame(np.where(validate_y == 0, -1, 1))

        tst = pd.concat([pd.DataFrame(test_x), test_y], axis=1)
        trg = pd.concat([pd.DataFrame(train_x), train_y], axis=1)
        val = pd.concat([pd.DataFrame(validate_x), validate_y], axis=1)

        tst.to_csv('data/{}_test.csv'.format(self.data_name()), index=False, header=False)
        trg.to_csv('data/{}_train.csv'.format(self.data_name()), index=False, header=False)
        val.to_csv('data/{}_validate.csv'.format(self.data_name()), index=False, header=False)

    @abstractmethod
    def _load_data(self):
        pass

    @abstractmethod
    def data_name(self):
        pass

    @abstractmethod
    def _preprocess_data(self):
        pass

    @abstractmethod
    def class_column_name(self):
        pass

    @abstractmethod
    def pre_training_adjustment(self, train_features, train_classes):
        """
        Perform any adjustments to training data before training begins.
        :param train_features: The training features to adjust
        :param train_classes: The training classes to adjust
        :return: The processed data
        """
        return train_features, train_classes

    def reload_from_hdf(self, hdf_path, hdf_ds_name, preprocess=True):
        self.log("Reloading from HDF {}".format(hdf_path))
        loader = copy.deepcopy(self)

        df = pd.read_hdf(hdf_path, hdf_ds_name)
        loader.load_and_process(data=df, preprocess=preprocess)
        loader.build_train_test_split()

        return loader

    def log(self, msg, *args):
        """
        If the learner has verbose set to true, log the message with the given parameters using string.format
        :param msg: The log message
        :param args: The arguments
        :return: None
        """
        if self._verbose:
            logger.info(msg.format(*args))

# these loaders where in the code when I initially loaded


class CreditDefaultData(DataLoader):

    def __init__(self, path='data/default of credit card clients.xls', verbose=False, seed=1):
        super().__init__(path, verbose, seed)

    def _load_data(self):
        self._data = pd.read_excel(self._path, header=1, index_col=0)

    def data_name(self):
        return 'CreditDefaultData'

    def class_column_name(self):
        return 'default payment next month'

    def _preprocess_data(self):
        pass

    def pre_training_adjustment(self, train_features, train_classes):
        """
        Perform any adjustments to training data before training begins.
        :param train_features: The training features to adjust
        :param train_classes: The training classes to adjust
        :return: The processed data
        """
        return train_features, train_classes


class CreditApprovalData(DataLoader):

    def __init__(self, path='data/crx.data', verbose=False, seed=1):
        super().__init__(path, verbose, seed)

    def _load_data(self):
        self._data = pd.read_csv(self._path, header=None)

    def data_name(self):
        return 'CreditApprovalData'

    def class_column_name(self):
        return '12'

    def _preprocess_data(self):
        # https://www.ritchieng.com/machinelearning-one-hot-encoding/
        to_encode = [0, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 15]
        label_encoder = preprocessing.LabelEncoder()
        one_hot = preprocessing.OneHotEncoder()

        df = self._data[to_encode]
        df = df.apply(label_encoder.fit_transform)

        # https://gist.github.com/ramhiser/982ce339d5f8c9a769a0
        vec_data = pd.DataFrame(one_hot.fit_transform(df[to_encode]).toarray())

        self._data = self._data.drop(to_encode, axis=1)
        self._data = pd.concat([self._data, vec_data], axis=1)

        # Clean any ?'s from the unencoded columns
        self._data = self._data[( self._data[[1, 2, 7]] != '?').all(axis=1)]

    def pre_training_adjustment(self, train_features, train_classes):
        return train_features, train_classes


class PenDigitData(DataLoader):
    def __init__(self, path='data/pendigits.csv', verbose=False, seed=1):
        super().__init__(path, verbose, seed)

    def _load_data(self):
        self._data = pd.read_csv(self._path, header=None)

    def class_column_name(self):
        return '16'

    def data_name(self):
        return 'PendDigitData'

    def _preprocess_data(self):
        pass

    def pre_training_adjustment(self, train_features, train_classes):
        return train_features, train_classes


class AbaloneData(DataLoader):
    def __init__(self, path='data/abalone.data', verbose=False, seed=1):
        super().__init__(path, verbose, seed)

    def _load_data(self):
        self._data = pd.read_csv(self._path, header=None)

    def data_name(self):
        return 'AbaloneData'

    def class_column_name(self):
        return '8'

    def _preprocess_data(self):
        pass

    def pre_training_adjustment(self, train_features, train_classes):
        return train_features, train_classes


class HTRU2Data(DataLoader):
    def __init__(self, path='data/HTRU_2.csv', verbose=False, seed=1):
        super().__init__(path, verbose, seed)

    def _load_data(self):
        self._data = pd.read_csv(self._path, header=None)

    def data_name(self):
        return 'HTRU2Data'

    def class_column_name(self):
        return '8'

    def _preprocess_data(self):
        pass

    def pre_training_adjustment(self, train_features, train_classes):
        return train_features, train_classes


class SpamData(DataLoader):
    def __init__(self, path='data/spambase.data', verbose=False, seed=1):
        super().__init__(path, verbose, seed)

    def _load_data(self):
        self._data = pd.read_csv(self._path, header=None)

    def data_name(self):
        return 'SpamData'

    def class_column_name(self):
        return '57'

    def _preprocess_data(self):
        pass

    def pre_training_adjustment(self, train_features, train_classes):
        return train_features, train_classes


class StatlogVehicleData(DataLoader):
    def __init__(self, path='data/statlog.vehicle.csv', verbose=False, seed=1):
        super().__init__(path, verbose, seed)

    def _load_data(self):
        self._data = pd.read_csv(self._path, header=None)

    def data_name(self):
        return 'StatlogVehicleData'

    def class_column_name(self):
        return '18'

    def _preprocess_data(self):
        to_encode = [18]
        label_encoder = preprocessing.LabelEncoder()

        df = self._data[to_encode]
        df = df.apply(label_encoder.fit_transform)

        self._data = self._data.drop(to_encode, axis=1)
        self._data = pd.concat([self._data, df], axis=1)

    def pre_training_adjustment(self, train_features, train_classes):
        return train_features, train_classes

#these are some of the loaders I made for different data. I based it off the way the other data was loaded.

class WhiteWine(DataLoader):
    def __init__(self, path='data/winequality-white.csv', verbose=False, seed=1):
        super().__init__(path, verbose, seed)

    def _load_data(self):
        self._data = pd.read_csv(self._path, header=None)

    def data_name(self):
        return 'WhiteWine'

    def class_column_name(self):
        return '11'

    def _preprocess_data(self):
        to_encode = [11]
        label_encoder = preprocessing.LabelEncoder()

        df = self._data[to_encode]
        df = df.apply(label_encoder.fit_transform)

        self._data = self._data.drop(to_encode, axis=1)
        self._data = pd.concat([self._data, df], axis=1)

    def pre_training_adjustment(self, train_features, train_classes):
        return train_features, train_classes


class SpamDataMlOrg(DataLoader):
    def __init__(self, path='data/dataset_44_spambase.csv', verbose=False, seed=1):
        super().__init__(path, verbose, seed)

    def _load_data(self):
        self._data = pd.read_csv(self._path, header=None)

    def data_name(self):
        return 'SpamDataMlOrg'

    def class_column_name(self):
        return '57'
    # igto a weird error about the data type which seemend to only be fixed if i used the label encorder.
    # This is a binary field but it seemend that in some of the data this is required based on type loaded in
    def _preprocess_data(self):
        to_encode = [57]
        label_encoder = preprocessing.LabelEncoder()

        df = self._data[to_encode]
        df = df.apply(label_encoder.fit_transform)

        self._data = self._data.drop(to_encode, axis=1)
        self._data = pd.concat([self._data, df], axis=1)

    def pre_training_adjustment(self, train_features, train_classes):
        return train_features, train_classes


class ElectricityMlOrg(DataLoader):
    def __init__(self, path='data/electricity-normalized.csv', verbose=False, seed=1):
        super().__init__(path, verbose, seed)

    def _load_data(self):
        self._data = pd.read_csv(self._path, header=None)

    def data_name(self):
        return 'ElectricityMlOrg'

    def class_column_name(self):
        return '8'

    # here i encoded the data but also down sampled it from the initial data set of 50k
    def _preprocess_data(self):
        to_encode = [8]
        label_encoder = preprocessing.LabelEncoder()
        classes = self._data[to_encode]
        classes = classes.apply(label_encoder.fit_transform)
        self._data = self._data.drop(to_encode, axis=1)
        self._data = pd.concat([self._data, classes], axis=1)
        # i brought the samples back down to about 7K. This is a bit arbitrary
        # this seemend like a good comprimise with the limited features
        data_total = self._data
        _, reduced_data = ms.train_test_split(data_total, test_size=.15, random_state=20, stratify=classes)
        reduced_data = pd.DataFrame(reduced_data)
        reduced_data.to_csv("reduced_electricity.csv")
        self._data = reduced_data

    def pre_training_adjustment(self, train_features, train_classes):
        return train_features, train_classes

class EegEyeState(DataLoader):
    def __init__(self, path='data/emotiveEEG.csv', verbose=False, seed=1):
        super().__init__(path, verbose, seed)

    def _load_data(self):
        self._data = pd.read_csv(self._path, header=None)

    def data_name(self):
        return 'EEG+EYE State'

    def class_column_name(self):
        return '14'

    # here i encoded the data but also down sampled it from the initial data set of 14k
    def _preprocess_data(self):
        to_encode = [14]
        label_encoder = preprocessing.LabelEncoder()
        classes = self._data[to_encode]
        classes = classes.apply(label_encoder.fit_transform)
        self._data = self._data.drop(to_encode, axis=1)
        self._data = pd.concat([self._data, classes], axis=1)
        # i brought the samples back down to about 7K. This is a bit arbitrary
        # this seemend like a good comprimise with the limited features
        data_total = self._data
        _, reduced_data = ms.train_test_split(data_total, test_size=.50, random_state=20, stratify=classes)
        reduced_data = pd.DataFrame(reduced_data)
        reduced_data.to_csv("reduced_eeg+eye.csv")
        self._data = reduced_data

    def pre_training_adjustment(self, train_features, train_classes):
        return train_features, train_classes

class Phishing(DataLoader):
    def __init__(self, path='data/phishing.csv', verbose=False, seed=1):
        super().__init__(path, verbose, seed)

    def _load_data(self):
        self._data = pd.read_csv(self._path, header=None)

    def data_name(self):
        return 'Phishing'

    def class_column_name(self):
        return '30'

    # here i encoded the data but also down sampled it from the initial data set of 11k
    def _preprocess_data(self):
        to_encode = [30]
        label_encoder = preprocessing.LabelEncoder()
        classes = self._data[to_encode]
        classes = classes.apply(label_encoder.fit_transform)
        self._data = self._data.drop(to_encode, axis=1)
        self._data = pd.concat([self._data, classes], axis=1)
        # i brought the samples back down to about 7K. This is a bit arbitrary
        # this seemend like a good comprimise with the limited features
        data_total = self._data
        _, reduced_data = ms.train_test_split(data_total, test_size=.60, random_state=20, stratify=classes)
        reduced_data = pd.DataFrame(reduced_data)
        reduced_data.to_csv("reduced_phishing.csv")
        self._data = reduced_data

    def pre_training_adjustment(self, train_features, train_classes):
        return train_features, train_classes

class MuskMlOrg(DataLoader):
    def __init__(self, path='data/musk.csv', verbose=False, seed=1):
        super().__init__(path, verbose, seed)

    def _load_data(self):
        self._data = pd.read_csv(self._path, header=None)

    def data_name(self):
        return 'Musk'

    def class_column_name(self):
        return '166'

    def _preprocess_data(self):
        to_encode = [166]
        label_encoder = preprocessing.LabelEncoder()

        df = self._data[to_encode]
        df = df.apply(label_encoder.fit_transform)

        self._data = self._data.drop(to_encode, axis=1)
        self._data = pd.concat([self._data, df], axis=1)

    def pre_training_adjustment(self, train_features, train_classes):
        return train_features, train_classes
