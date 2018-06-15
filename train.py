# Train model, generate prediction and submission.
# Sample usage:
#   python train.py -c config_name  # to cross validation
#   python train.py -c config_name -s  # to predict and generate submission:
#
# TODO:
# 1. Add option to print erroneous rows in cross validation.

import datetime
import json
import math
import os
import pickle
import time
from optparse import OptionParser
from tensorflow.python.lib.io import file_io

import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import KFold

from configs import config_map
# TODO: move constants used across files to a single file
from feature_generator import PICKLE_FOLDER, TARGET_PATH
from models import model_map

TRAIN_SIZE = 1503424
TEST_SIZE = 508438
SUBMISSION_FOLDER = 'submissions/'
RECORD_FOLDER = 'records/'
CV_RECORD_FOLDER = RECORD_FOLDER + 'cv/'
SUBMISSION_RECORD_FOLDER = RECORD_FOLDER + 'sub/'


# Prepares train/test data. Target column will be returned when get train data;
# when get test data, it will be None.
# Two things to note:
#   1. All the feature pickles should be generated before training;
#   2. Order of training data should not be changed if you want to
#      compare result between trainings, as cross validation depends
#      on that.
def prepare_data(feature_names, pickle_folder_path, test=False):
    DATA_LENTH = TEST_SIZE if test else TRAIN_SIZE

    features = []
    total_feature = 0
    for name in feature_names:
        # Assume all the feature pickles are generated. Any features not
        # generated will cause an error here.
        # pickle_path = PICKLE_FOLDER + name
        pickle_path = pickle_folder_path + name
        if test:
            pickle_path += '_test'
        # feature = pd.read_pickle(pickle_path)
        with file_io.FileIO(pickle_path, mode='rb') as feature_input:
            feature = pickle.load(feature_input)

        # Sanity check
        assert(feature.shape[0] == DATA_LENTH)
        if isinstance(feature, pd.DataFrame):
            total_feature += feature.shape[1]
        else:
            # Series
            total_feature += 1

        features.append(feature)

    X = pd.concat(features, axis=1)
    y = None
    if not test:
        y = pd.read_pickle(TARGET_PATH)

    # Sanity check
    assert(X.shape == (DATA_LENTH, total_feature))
    print("Data size:", X.shape)
    if not test:
        assert(y.shape == (TRAIN_SIZE,))
        print("Label size:", y.shape)

    return X, y


# Retrieves the model class from model map and creates an instance of it.
def get_model(model_name, model_params):
    return model_map[model_name](model_params=model_params)


# TODO: figure out query json file for analysis.
# TODO: put utility functions in a separate file.
# Note that record_cv will change config (remove tune params), but it shouldn't
# matter in training and predicting.
# TODO: figure out a better way to handle tuning parameters.
def record_cv(config, val_errors, train_errors, output_path, timestamp=datetime.datetime.now().strftime("%m-%d_%H:%M:%S")):
    # Remove tune_params from config, as it is not serializable, and we do
    # not need to record it.
    # config.pop('tune_params')
    record_dict = {
        'config': config,
        'train_errors': train_errors,
        'val_errors': val_errors,
        'sub_error': 0 # Need to fill manually after submission.
    }
    # if not os.path.exists(CV_RECORD_FOLDER):
    #     os.makedirs(CV_RECORD_FOLDER)
    # with open(
    #     '%s%s_%s' %(CV_RECORD_FOLDER, config['name'], timestamp),
    #     'w'
    # ) as fp:
    #     json.dump(record_dict, fp)
    with file_io.FileIO(output_path + "/result.json", mode='w') as fp:
        json.dump(record_dict, fp)



# Returns two array containing validation and train errors of each fold.
def cross_validate(config, X, y):
    model_name = config['model']
    model_params = config['model_params']
    folds = config['folds']

    kf = KFold(n_splits=folds, shuffle=True, random_state=42)

    train_errors = []
    val_errors = []
    for i, (train_index, val_index) in enumerate(kf.split(X, y)):
        print('Fold ', i)

        X_train, y_train = X.iloc[train_index], y.iloc[train_index]
        X_val,y_val = X.iloc[val_index], y.iloc[val_index]

        print('training...')
        model = get_model(model_name, model_params)
        model.fit(X_train, y_train)
        train_rmse = math.sqrt(
            mean_squared_error(y_train, model.predict(X_train)))
        print('training error: ', train_rmse)
        train_errors.append(train_rmse)

        print('validating...')
        rmse = math.sqrt(mean_squared_error(y_val, model.predict(X_val)))
        print('validation error: ', rmse)
        val_errors.append(rmse)

        print('-----------------------------------------')

    print('\nAvg validation error: ', np.mean(val_errors))
    return val_errors, train_errors


# Separates the cross validation with the data preparation step. The main purpose is
# we do not need to repeat data preparation when tuning a model.
def train(config, pickle_folder_path, output_path, record=True):
    # Prepare train data.
    feature_names = config['features']
    X, y = prepare_data(feature_names, pickle_folder_path, test=False)
    # For debug use only
    # print(X.columns)
    # print(X.describe(include='all'))
    # print(y.describe())
    # print(X.head())
    # print(y.head())
    # print(X.index)
    # print(y.index)
    # X = X[:500]
    # y = y[:500]
    val_errors, train_errors = cross_validate(config, X, y)
    # Records the cross validation in a json file if needed.
    if record:
        record_cv(config, val_errors, train_errors, output_path)


# Predicts on test data and generates submission.
def predict(config, cv=True):
    feature_names = config['features']
    model_name = config['model']
    model_params = config['model_params']

    # Prepares train data.
    X_train, y_train = prepare_data(feature_names, test=False)
    X_test, _ = prepare_data(feature_names, test=True)

    # Timestamp for naming of the submission file and the cv record file.
    sub_timestamp = datetime.datetime.now().strftime("%m-%d_%H:%M:%S")

    # Cross-validates with the config to record the local validation errors.
    if cv:
        print('Cross validating and recording local cv result...')
        val_errors, train_errors = cross_validate(config, X_train, y_train)
        record_cv(config, val_errors, train_errors, sub_timestamp)

    print('training on entire dataset...')
    model = get_model(model_name, model_params)
    model.fit(X_train, y_train)
    rmse = math.sqrt(mean_squared_error(y_train, model.predict(X_train)))
    print('training error: ', rmse)

    print('predicting...')
    prediction = model.predict(X_test)
    # Clips predictions to be between 0 and 1.
    np.clip(prediction, 0, 1, out=prediction)
    # Sanity check.
    assert(len(prediction) == TEST_SIZE)

    submission = pd.read_csv('data/sample_submission.csv')
    # Sample submission file and test dataset has the same item_id
    # in the same order.
    submission['deal_probability'] = prediction

    # Submission history folder is a sub directory of submission folder, thus
    # the following command will create both on the way.
    if not os.path.exists(SUBMISSION_RECORD_FOLDER):
        os.makedirs(SUBMISSION_RECORD_FOLDER)

    if not os.path.exists(SUBMISSION_FOLDER):
        os.makedirs(SUBMISSION_FOLDER)
    # Generates submission csv.
    submission.to_csv(
        '%s%s_%s.csv' %(SUBMISSION_FOLDER, config['name'], sub_timestamp),
        index=False
    )
    # Saves the submission and its config as pickle for future investigation.
    submission_history = {
        'config': config,
        'submission': submission
    }
    sub_history_file = open(
        '%s%s_%s' %(
            SUBMISSION_RECORD_FOLDER, config['name'], sub_timestamp),
        'wb')
    pickle.dump(submission_history, sub_history_file)
    # TODO: use kaggle cmd line api to submit and get result.
    # TODO: centralize records, now we have cv records (in json) and
    #       submission history (in pickle).


if __name__ == '__main__':
    t_start = time.time()
    # Parser to parse cmd line option
    parser = OptionParser()
    # Adds options to parser, currently only config file
    parser.add_option(
        '-c', '--config', action='store', type='string', dest='config')
    parser.add_option(
        '-s', '--submit', action='store_true', dest='submit', default=False)
    # Skips cross validation and record when generate submission.
    parser.add_option(
        '-n', '--no_cv', action='store_false', dest='cv', default=True)
    # Pickle file path on gcloud
    parser.add_option(
        '-t', '--train-files', action='store', type='string', dest='pickle_folder_path')
    # Base job path on gcloud
    parser.add_option(
        '-j', '--job-dir', action='store', type='string', dest='output_path')

    options, _ = parser.parse_args()
    config = config_map[options.config]
    # Adds a name fields for the naming of submission / record files.
    config['name'] = options.config
    if options.submit:
        # Predicts on test set and generates submission files.
        predict(config, options.cv)
    else:
        # Cross validation.
        train(config, options.pickle_folder_path, options.output_path)

    t_finish = time.time()
    print('Total running time: ', (t_finish - t_start) / 60)
