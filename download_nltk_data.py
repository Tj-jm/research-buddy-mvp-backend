import nltk

# Custom download directory
download_dir = "./nltk_data"

# Download only what's needed for POS-enhanced vectorizer
nltk.download("punkt", download_dir=download_dir)
nltk.download("averaged_perceptron_tagger", download_dir=download_dir)
nltk.download("maxent_ne_chunker", download_dir=download_dir)
nltk.download("words", download_dir=download_dir)
