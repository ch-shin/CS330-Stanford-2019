import numpy as np
import random
# import tensorflow as tf
import tensorflow.compat.v1 as tf
tf.disable_v2_behavior()
from load_data import DataGenerator
from tensorflow.python.platform import flags
from tensorflow.keras import layers
from tensorflow.keras import backend as K

FLAGS = flags.FLAGS

flags.DEFINE_integer(
    'num_classes', 5, 'number of classes used in classification (e.g. 5-way classification).')

flags.DEFINE_integer('num_samples', 1,
                     'number of examples used for inner gradient update (K for K-shot learning).')

flags.DEFINE_integer('meta_batch_size', 16,
                     'Number of N-way classification tasks per batch')


def loss_function(preds, labels):
    """
    Computes MANN loss
    Args:
        preds: [B, K+1, N, N] network output
        labels: [B, K+1, N, N] labels
    Returns:
        scalar loss
    """
    #############################
    #### YOUR CODE GOES HERE ####
    preds_target = preds[:, -1:, :, :]
    labels_target = labels[:, -1:, :, :]
    loss = K.mean(K.categorical_crossentropy(labels_target, preds_target, from_logits=True))

    return loss
    #############################


class MANN(tf.keras.Model):

    def __init__(self, num_classes, samples_per_class):
        super(MANN, self).__init__()
        self.num_classes = num_classes
        self.samples_per_class = samples_per_class
        self.layer1 = tf.keras.layers.LSTM(128, return_sequences=True)
        self.layer2 = tf.keras.layers.LSTM(num_classes, return_sequences=True)

    def call(self, input_images, input_labels):
        """
        MANN
        Args:
            input_images: [B, K+1, N, 784] flattened images
            labels: [B, K+1, N, N] ground truth labels
        Returns:
            [B, K+1, N, N] predictions
        """
        #############################
        #### YOUR CODE GOES HERE ####
        K = input_images.shape[1] - 1
        N = input_images.shape[2]
        seen = tf.concat([input_images[:,0:-1,:,:],
                          input_labels[:,0:-1,:,:]], axis=-1)
        unseen = tf.concat([input_images[:,-1:,:,:],
                           tf.zeros_like(input_labels)[:,-1:,:,:]], axis=-1)
        input_concatenated = tf.concat([seen, unseen], axis=1)
        input_concatenated = tf.reshape(input_concatenated, [-1, (K+1)*N, 784+N])
        out = self.layer1(input_concatenated)
        out = self.layer2(out)
        out = tf.reshape(tensor=out, shape=(-1, K + 1, N, N))
        #############################
        return out

ims = tf.placeholder(tf.float32, shape=(None, FLAGS.num_samples + 1, FLAGS.num_classes, 784))
labels = tf.placeholder(tf.float32, shape=(None, FLAGS.num_samples + 1, FLAGS.num_classes, FLAGS.num_classes))

data_generator = DataGenerator(
    FLAGS.num_classes, FLAGS.num_samples + 1)

o = MANN(FLAGS.num_classes, FLAGS.num_samples + 1)
out = o(ims, labels)

loss = loss_function(out, labels)
optim = tf.train.AdamOptimizer(0.001)
optimizer_step = optim.minimize(loss)

with tf.Session() as sess:
    sess.run(tf.local_variables_initializer())
    sess.run(tf.global_variables_initializer())

    for step in range(50000):
        i, l = data_generator.sample_batch('train', FLAGS.meta_batch_size)
        feed = {ims: i.astype(np.float32), labels: l.astype(np.float32)}
        _, ls = sess.run([optimizer_step, loss], feed)

        if step % 100 == 0:
            print("*" * 5 + "Iter " + str(step) + "*" * 5)
            i, l = data_generator.sample_batch('test', 423)  # takes all the data
            feed = {ims: i.astype(np.float32),
                    labels: l.astype(np.float32)}
            pred, tls = sess.run([out, loss], feed)
            print("Train Loss:", ls, "Test Loss:", tls)
            pred = tf.reshape(pred,
                              (-1, FLAGS.num_samples + 1,
                               FLAGS.num_classes, FLAGS.num_classes)
                              )
            pred = pred[:, -1, :, :].eval().argmax(2)
            l = l[:, -1, :, :].argmax(2)
            print("Test Accuracy", (1.0 * (pred == l).mean()))
