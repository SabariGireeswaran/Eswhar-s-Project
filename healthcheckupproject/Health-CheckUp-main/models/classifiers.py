import os
import cv2
import csv
import json
import pickle
import numpy as np
import pandas as pd
import matplotlib.cm as cm
from PIL import Image
from models.utils import *

from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC

import tensorflow as tf
from tensorflow.keras.models import load_model , model_from_json
from tensorflow.keras.preprocessing import image
from tensorflow.keras.preprocessing.image import img_to_array , array_to_img , load_img

# model1 = ''
# model2 = ''
# model3 = ''
# model4 = ''
# model5 = ''

ALZHEIMER_MODEL_PATH = "models/alzheimer-model.h5"
model1 = None

# The Alzheimer model is too large for GitHub, so load it only when needed
# instead of at import time; the rest of the site works without it.
def get_alzheimer_model():
    global model1
    if model1 is None:
        if not os.path.exists(ALZHEIMER_MODEL_PATH):
            raise FileNotFoundError(
                f"{ALZHEIMER_MODEL_PATH} not found. Download it and place it in the models folder (see README).")
        model1 = load_model(ALZHEIMER_MODEL_PATH)
    return model1



_pickle_model_cache = {}

def _load_pickle_model(path):
    # Load each .pkl once per process instead of unpickling it on every
    # request.
    if path not in _pickle_model_cache:
        with open(path, 'rb') as file:
            _pickle_model_cache[path] = pickle.load(file)
    return _pickle_model_cache[path]

def predict_diabetes(features):
    model = _load_pickle_model('models/diabetes-model.pkl')
    pred = model.predict(features)
    return int(pred[0])

def predict_heartD(features):
    model = _load_pickle_model('models/heart-model.pkl')
    pred = model.predict(features)
    return int(pred[0])



def predict_liverD(features):
    model = _load_pickle_model('models/liver-model.pkl')
    pred = model.predict(features)
    return int(pred[0])

def make_gradcam_heatmap(img_array, model, last_conv_layer_name, pred_index=None):
    grad_model = tf.keras.models.Model([model.inputs], [model.get_layer(last_conv_layer_name).output, model.output])
    model.layers[-1].activation = None

    with tf.GradientTape() as tape:
        last_conv_layer_output, preds = grad_model(img_array)
        if pred_index is None:
            pred_index = tf.argmax(preds[0])
        class_channel = preds[:, pred_index]
        
    grads = tape.gradient(class_channel, last_conv_layer_output)
    pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))

    last_conv_layer_output = last_conv_layer_output[0]
    heatmap = last_conv_layer_output @ pooled_grads[..., tf.newaxis]
    
    heatmap = tf.squeeze(heatmap)
    heatmap = tf.maximum(heatmap, 0) / tf.math.reduce_max(heatmap)
    
    return heatmap.numpy()

def save_and_display_gradcam(img_path, heatmap, cam_path, alpha=0.9):
    img = load_img(img_path)
    img = img_to_array(img)

    heatmap = np.uint8(255 * heatmap)
    jet = cm.get_cmap("jet")
    jet_colors = jet(np.arange(256))[:, :3]
    jet_heatmap = jet_colors[heatmap]
    jet_heatmap = array_to_img(jet_heatmap)
    
    jet_heatmap = jet_heatmap.resize((img.shape[1], img.shape[0]))
    jet_heatmap = img_to_array(jet_heatmap)

    superimposed_img = jet_heatmap * alpha + img
    superimposed_img = array_to_img(superimposed_img)

    superimposed_img.save(cam_path)

def predict_alzheimer(img , img_path , cam_path):
    img = np.asarray(img, dtype=np.float32)/255.0
    img = img.reshape((1, *img.shape))
    class2label = {0: 'Mild Demented', 1: 'Moderate Demented', 2: 'Non Demented', 3: 'Very Mild Demented'}
    model = get_alzheimer_model()
    pred = class2label[np.argmax(model.predict(img)[0])]

    heatmap = make_gradcam_heatmap(img, model, 'block5_pool')
    save_and_display_gradcam(img_path, heatmap, cam_path, alpha=0.9)
    return pred , cam_path






_disease_model_cache = None

def _get_disease_model():
    # Training a RandomForest and re-reading the CSV lookup tables on every
    # single request was the previous behaviour; cache everything after the
    # first call instead.
    global _disease_model_cache
    if _disease_model_cache is not None:
        return _disease_model_cache

    training = pd.read_csv('models/training.csv')
    cols = training.columns[:-1]
    x = training[cols]
    y = training['prognosis']
    le = LabelEncoder()
    y = le.fit_transform(y)

    x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.25, random_state=42)
    clf = RandomForestClassifier(random_state=42).fit(x_train, y_train)

    symptoms_dict = {}
    for index, symptom in enumerate(x):
        symptoms_dict[symptom] = index

    severity_dict = {}
    description_dict = {}
    precautions_dict = {}

    with open('models/symptom_description.csv') as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        for row in csv_reader:
            description_dict[row[0]] = row[1]

    with open('models/symptom_severity.csv') as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        try:
            for row in csv_reader:
                severity_dict[row[0]] = int(row[1])
        except:
            pass

    with open('models/symptom_precaution.csv') as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        for row in csv_reader:
            precautions_dict[row[0]] = [row[1], row[2], row[3], row[4]]

    _disease_model_cache = {
        'clf': clf,
        'le': le,
        'symptoms_dict': symptoms_dict,
        'severity_dict': severity_dict,
        'description_dict': description_dict,
        'precautions_dict': precautions_dict,
    }
    return _disease_model_cache


def predict_disease(user_symptoms, days=5):
    cache = _get_disease_model()
    clf = cache['clf']
    le = cache['le']
    symptoms_dict = cache['symptoms_dict']
    severity_dict = cache['severity_dict']
    description_dict = cache['description_dict']
    precautions_dict = cache['precautions_dict']

    input_vector = np.zeros(len(symptoms_dict))
    output = {}
    severity = 0
    advice = ''
    for item in user_symptoms:
        input_vector[[symptoms_dict[item]]] = 1
        severity += severity_dict[item]
        if((severity*days)/(len(user_symptoms) + 1)) > 10:
            advice = "You should take the consultation from the doctor."
        else:
            advice = "The situation is not as bad as of now but you should take precautions. If symptoms still persist then you should go to the doctor."

    for i in list(le.inverse_transform(np.argsort(clf.predict_proba([input_vector])[0])[::-1])[:3]):
        output[i] = {}
        output[i]['desc'] = description_dict[i]
        output[i]['prec'] = precautions_dict[i]

    return advice , output


