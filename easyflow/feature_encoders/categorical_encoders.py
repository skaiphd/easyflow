"""
Interface to use tensorflow feature columns with Keras. Only most used encoders
"""
import tensorflow as tf

from .base import BaseFeatureColumnEncoder


def get_unique_vocabulary(dataset=None, features=None):
    """Get feature vocabulary list

    Args:
        dataset (tf.data.Dataset): Features Data to apply encoder on.
        features (list): list of feature names

    Returns:
        (dict): dictionary containing list of unique vocabulary values for each feature
    """
    if hasattr(dataset, '_batch_size'):
        # unbatch dataset
        dataset = dataset.unbatch()

    if isinstance(dataset.element_spec, tuple):
        map_func = lambda x, y: x[feature]
    else:
        map_func = lambda x: x[feature]

    feature_vocab_list = {}
    for feature in features:
        feature_ds = dataset.map(map_func)\
                            .apply(tf.data.experimental.unique())\
                            .as_numpy_iterator()
        uniq_vocab = list(feature_ds)
        if all(map(lambda x: isinstance(x, bytes), uniq_vocab)):
            # map bytes to ensure objects are serializable when saving model
            uniq_vocab = [str(value, 'utf-8') for value in uniq_vocab]
        feature_vocab_list[feature] = tf.feature_column.categorical_column_with_vocabulary_list(feature, uniq_vocab)
    return feature_vocab_list


class BaseCategoricalFeatureColumnEncoder(BaseFeatureColumnEncoder):
    """Base class for categorical type encoders
    """
    def __init__(self, feature_transformer=None, **kwargs):
        super().__init__(feature_transformer=feature_transformer, **kwargs)

    def encode(self, dataset=None, features=None):
        """Apply feature encoding that requires unique vocabulary as input

        Args:
            dataset (tf.data.Dataset): Features Data to apply encoder on.
            features (list): list of feature names

        Returns:
            (list): list of encoded features
        """
        feature_vocab_list = get_unique_vocabulary(dataset, features)
        return [self.feature_transformer(feature_vocab_list[feature], **self.kwargs) for feature in features]


class CategoricalFeatureEncoder(BaseCategoricalFeatureColumnEncoder):
    """
    Class encodes Categorical features using tensorflow feature_columns. This is a wrapper to
    tf.feature_column.indicator_column to conform to the BaseFeatureColumnEncoder interface and does not change the behaviour.

    Examples
    --------
    >>> data = {'feature': ['a', 'b', 'c', 'c']}
    >>> dataset=tf.data.Dataset.from_tensor_slices(data).batch(4)
    >>> example_batch = next(iter(dataset))
    >>> feature_layer = lambda feature_column, batch: tf.keras.layers.DenseFeatures(feature_column)(batch).numpy()
    >>> encoder = CategoricalFeatureEncoder()
    >>> encoded_feature = encoder.encode(dataset, ['feature'])
    >>> feature_layer(encoded_feature, example_batch)
        array([[1., 0., 0.],
               [0., 1., 0.],
               [0., 0., 1.],
               [0., 0., 1.]], dtype=float32)
    """
    def __init__(self, **kwargs):
        super().__init__(feature_transformer=tf.feature_column.indicator_column, **kwargs)


class EmbeddingFeatureEncoder(BaseCategoricalFeatureColumnEncoder):
    """
    Class encodes high cardinality Categorical features(Embeddings) using tensorflow feature_columns. This is a wrapper to
    tf.feature_column.embedding_column to conform to the BaseFeatureColumnEncoder interface and does not change the behaviour.

    Examples
    --------
    >>> data = data = {'feature': ['a', 'b', 'c', 'c', 'c', 'c', 'd', 'd', 'd']}
    >>> dataset=tf.data.Dataset.from_tensor_slices(data).batch(4)
    >>> example_batch = next(iter(dataset))
    >>> feature_layer = lambda feature_column, batch: tf.keras.layers.DenseFeatures(feature_column)(batch).numpy()
    >>> encoder = EmbeddingFeatureEncoder(dimension=2)
    >>> encoded_feature = encoder.encode(dataset, ['feature'])
    >>> feature_layer(encoded_feature, example_batch)
        # results will differ due the randomness
        array([[-0.5162831 , -0.18130358],
               [ 0.50860345, -0.00483216],
               [ 0.00722361,  0.14289041],
               [ 0.00722361,  0.14289041]], dtype=float32)
    """
    def __init__(self, **kwargs):
        super().__init__(feature_transformer=tf.feature_column.embedding_column, **kwargs)


class CategoryCrossingFeatureEncoder(BaseCategoricalFeatureColumnEncoder):
    """Class creates cross column features using tensorflow feature_columns. This is a wrapper to
    tf.feature_column.crossed_column to conform to the BaseFeatureColumnEncoder interface and does not change the behaviour.

    Examples
    --------
    >>> data = {'feature_a': ['a', 'b', 'c', 'c', 'c', 'c', 'd', 'd', 'd'],
                'feature_b': ['e', 'f', 'g', 'g', 'g', 'g', 'g', 'g', 'g']}
    >>> dataset=tf.data.Dataset.from_tensor_slices(data).batch(4)
    >>> example_batch = next(iter(dataset))
    >>> feature_layer = lambda feature_column, batch: tf.keras.layers.DenseFeatures(feature_column)(batch).numpy()
    >>> encoder = CategoryCrossingFeatureEncoder(hash_bucket_size=3)
    >>> encoded_feature = encoder.encode(dataset, ['feature_a', 'feature_b'])
    >>> feature_layer(encoded_feature, example_batch)
        array([[0., 0., 1.],
               [1., 0., 0.],
               [0., 0., 1.],
               [0., 0., 1.]], dtype=float32)
    """
    def __init__(self, **kwargs):
        super().__init__(feature_transformer=tf.feature_column.crossed_column, **kwargs)

    def encode(self, dataset=None, features=None):
        """Apply Cross column feature engineering follow by indicator column

        Args:
            dataset (tf.data.Dataset): Features Data to apply encoder on.
            features (list): list of feature names

        Returns:
            (list): list of encoded features
        """
        feature_vocab_list = get_unique_vocabulary(dataset, features)
        crossed_features = self.feature_transformer(feature_vocab_list, **self.kwargs)
        crossed_features = tf.feature_column.indicator_column(crossed_features)
        return crossed_features
