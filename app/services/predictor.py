import numpy as np
import tensorflow as tf
from keras.preprocessing.sequence import pad_sequences


def predict_label(abstract, model_name, models, tokenizers, label_encoder):
    def predict_one(model_key):
        model = models[model_key]
        confidence = None

        if model_key in ['SVM','MNB','Random Forest','AdaBoost','KNN','XG_BOOST']:
            x_input = tokenizers['TFIDF'].transform([abstract])
            pred_idx = model.predict(x_input)[0]
            if hasattr(model, 'predict_proba'):
                confidence = model.predict_proba(x_input)[0][pred_idx]

        elif model_key == 'Feedforward NN':
            x_input_dense = tokenizers['TFIDF'].transform([abstract]).toarray()
            y_probs = model.predict(x_input_dense, verbose=0)[0]
            pred_idx = np.argmax(y_probs)
            confidence = y_probs[pred_idx]

        elif model_key == 'BiLSTM':
            seq = tokenizers["NN"].texts_to_sequences([abstract])
            padded_seq = pad_sequences(seq, maxlen=300)
            y_probs = model.predict(padded_seq, verbose=0)[0]
            pred_idx = np.argmax(y_probs)
            confidence = y_probs[pred_idx]

        elif model_key == 'BERT':
            bert_inputs = tokenizers['BERT'](
                abstract,
                return_tensors='tf',
                padding=True,
                truncation=True,
                max_length=256
            )
            logits = model(**bert_inputs).logits
            probs = tf.nn.softmax(logits, axis=1).numpy()[0]
            pred_idx = np.argmax(probs)
            confidence = probs[pred_idx]

        else:
            raise ValueError(f"Unsupported model: {model_key}")

        label = label_encoder.inverse_transform([pred_idx])[0]
        return label, round(confidence, 4) if confidence else None

    # If ALL: Run all models
    if model_name == "ALL":
        results = {}
        for key in models:
            try:
                label, conf = predict_one(key)
                results[key] = {"label": label, "confidence": conf}
            except Exception as e:
                results[key] = {"error": str(e)}
        return results, None

    # If not ALL: Run single model
    return predict_one(model_name)




