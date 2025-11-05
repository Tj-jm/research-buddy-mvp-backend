import joblib
from transformers import TFBertForSequenceClassification, BertTokenizerFast
from pathlib import Path
import pickle
from keras.models import load_model

from app.config import DATA_DIR
print (DATA_DIR)
def load_all_models():
    models = {
        "SVM": joblib.load(DATA_DIR/"svm_model_light.pkl"),
        "MNB":joblib.load(DATA_DIR/"mnb_model_light.pkl"),
        "Random Forest": joblib.load(DATA_DIR / "rf_model_light.pkl"),
        "AdaBoost": joblib.load(DATA_DIR / "ada_model_light.pkl"),
        "KNN": joblib.load(DATA_DIR / "knn_classifier_light.pkl"),
        "Feedforward NN": load_model(DATA_DIR / "feedforward_model_light.h5"),
        "XG_BOOST": joblib.load(DATA_DIR / "xgb_model_light.pkl"),
        "BiLSTM": load_model(DATA_DIR / "bilstm_model_light.h5"),
        "BERT": TFBertForSequenceClassification.from_pretrained(str(DATA_DIR / "bert_model_light"))
    }
    

    tokenizers = {
        "TFIDF": joblib.load(DATA_DIR / "tfidf_vectorizer_light_v2.pkl"),
        "NN": joblib.load(DATA_DIR / "nn_tokenizer.pkl"),
        "BERT": BertTokenizerFast.from_pretrained(str(DATA_DIR / "bert_tokenizer_light"))
    }

    label_encoder = joblib.load(DATA_DIR / "label_encoder_light_v2.pkl")
    tfidf_vectorizer = tokenizers["TFIDF"]

    return models, tokenizers, label_encoder,tfidf_vectorizer



