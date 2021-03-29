"""base classes for stateful preprocessing layers"""
from abc import ABC, abstractmethod

import tensorflow as tf


def one2one_func(x):
    """helper method to apply one to one preprocessor"""
    return x


def extract_feature_column(dataset, name):
    dataset = dataset.map(lambda x, y: x[name])
    dataset = dataset.map(lambda x: tf.expand_dims(x, -1))
    return dataset


class BaseFeatureTransformer:
    """Apply column based transformation on the data

    Args:
        feature_encoder_list : 
    """
    def __init__(self, feature_encoder_list=None):
        self.feature_encoder_list = feature_encoder_list
        features = self.feature_encoder_list[0][2]
        self.adapted_preprocessors = {feature_name: one2one_func for feature_name in features}

    @abstractmethod
    def transform(self, dataset):
        """Apply feature encodings on supplied list

        Args:
            X (tf.data.Dataset): Features Data to apply encoder on.

        Returns:
            (list, list): Keras inputs for each feature and list of encoders
        """

    def create_inputs(self, features, dtype):
        """Create inputs for Keras Model

        Returns:
            list: list of keras inputs
        """
        return [tf.keras.Input(shape=(), name=feature, dtype=dtype) for feature in features]

    def _warm_up(self, dataset, preprocessor, features, feature_inputs):
        """Apply feature encodings on supplied list

        Args:
            X (tf.data.Dataset): Features Data to apply encoder on.

        Returns:
            (list, list): Keras inputs for each feature and list of encoders
        """
        encoded_features = {}
        for feature_input, feature_name in zip(feature_inputs, features):
            _preprocessor = preprocessor()
            feature_ds = extract_feature_column(dataset, feature_name)
            feature_ds = feature_ds.map(self.adapted_preprocessors[feature_name])
            _preprocessor.adapt(feature_ds)
            encoded_feature = _preprocessor(feature_input)
            encoded_features[feature_name] = encoded_feature
            self.adapted_preprocessors[feature_name] = _preprocessor
        return encoded_features

    def __len__(self):
        return len(self.feature_encoder_list)
