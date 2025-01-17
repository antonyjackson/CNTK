import sys
import os
from cntk import Trainer, Axis
from cntk.io import MinibatchSource, CTFDeserializer, StreamDef, StreamDefs,\
        INFINITELY_REPEAT, FULL_DATA_SWEEP
from cntk.learner import sgd, learning_rate_schedule, UnitType
from cntk.ops import input_variable, cross_entropy_with_softmax, \
        classification_error, sequence
from cntk.utils import ProgressPrinter

abs_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(abs_path, "..", "..", "..", "Examples", "common"))
from nn import LSTMP_component_with_self_stabilization as simple_lstm
from nn import embedding, linear_layer


# Creates the reader
def create_reader(path, is_training, input_dim, label_dim):
    return MinibatchSource(CTFDeserializer(path, StreamDefs(
        features=StreamDef(field='x', shape=input_dim, is_sparse=True),
        labels=StreamDef(field='y', shape=label_dim, is_sparse=False)
        )), randomize=is_training,
        epoch_size=INFINITELY_REPEAT if is_training else FULL_DATA_SWEEP)


# Defines the LSTM model for classifying sequences
def LSTM_sequence_classifer_net(input, num_output_classes, embedding_dim,
                                LSTM_dim, cell_dim):
    embedded_inputs = embedding(input, embedding_dim)
    lstm_outputs = simple_lstm(embedded_inputs, LSTM_dim, cell_dim)[0]
    thought_vector = sequence.last(lstm_outputs)
    return linear_layer(thought_vector, num_output_classes)


# Creates and trains a LSTM sequence classification model
def train_sequence_classifier(debug_output=False):
    input_dim = 2000
    cell_dim = 25
    hidden_dim = 25
    embedding_dim = 50
    num_output_classes = 5

    # Input variables denoting the features and label data
    features = input_variable(shape=input_dim, is_sparse=True)
    label = input_variable(num_output_classes, dynamic_axes=[
                           Axis.default_batch_axis()])

    # Instantiate the sequence classification model
    classifier_output = LSTM_sequence_classifer_net(
        features, num_output_classes, embedding_dim, hidden_dim, cell_dim)

    ce = cross_entropy_with_softmax(classifier_output, label)
    pe = classification_error(classifier_output, label)

    rel_path = ("../../../Tests/EndToEndTests/Text/" +
                "SequenceClassification/Data/Train.ctf")
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), rel_path)

    reader = create_reader(path, True, input_dim, num_output_classes)

    input_map = {
            features: reader.streams.features,
            label:    reader.streams.labels
    }

    lr_per_sample = learning_rate_schedule(0.0005, UnitType.sample)
    # Instantiate the trainer object to drive the model training
    trainer = Trainer(classifier_output, (ce, pe),
                      sgd(classifier_output.parameters, lr=lr_per_sample))

    # Get minibatches of sequences to train with and perform model training
    minibatch_size = 200

    pp = ProgressPrinter(0)
    for i in range(255):
        mb = reader.next_minibatch(minibatch_size, input_map=input_map)
        trainer.train_minibatch(mb)
        pp.update_with_trainer(trainer, True)

    evaluation_average = float(trainer.previous_minibatch_evaluation_average)
    loss_average = float(trainer.previous_minibatch_loss_average)
    return evaluation_average, loss_average

if __name__ == '__main__':
    error, _ = train_sequence_classifier()
    print(" error: %f" % error)
