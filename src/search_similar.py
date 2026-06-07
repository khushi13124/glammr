import numpy as np
import os
import pickle
import re
import cv2
from tensorflow.keras.applications.resnet50 import ResNet50, preprocess_input
from tensorflow.keras.preprocessing import image
from tensorflow.keras.models import Model
import matplotlib.pyplot as plt
from PIL import Image

# Paths
IMG_DIR = r'D:\Khushi Patel\Indus\Sem-7\SGP\data\deepfashion\img'
FEATURES_FILE = r'D:\Khushi Patel\Indus\Sem-7\SGP\features.pkl'
QUERY_IMAGE = r'D:\Khushi Patel\Indus\Sem-7\SGP\t3.png'

# Load ResNet50 model
base_model = ResNet50(weights='imagenet', include_top=False, pooling='avg')
model = Model(inputs=base_model.input, outputs=base_model.output)

def extract_features(img_path):
    """Extract features after masking face region"""
    img = image.load_img(img_path, target_size=(224, 224))
    x = image.img_to_array(img)
    x[:int(x.shape[0] * 0.30), :, :] = 0  # Remove top 30% (likely face)
    x = np.expand_dims(x, axis=0)
    x = preprocess_input(x)
    return model.predict(x, verbose=0).flatten()

def get_dominant_color(img_path):
    """Detect dominant BGR color using KMeans"""
    img = cv2.imread(img_path)
    if img is None:
        return np.array([0, 0, 0])
    img = cv2.resize(img, (50, 50)).reshape(-1, 3).astype(np.float32)
    _, _, centers = cv2.kmeans(img, 1, None, (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0),
                               10, cv2.KMEANS_RANDOM_CENTERS)
    return centers[0]

def cosine_similarity(v1, v2):
    return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

def color_distance(c1, c2):
    return np.linalg.norm(c1 - c2)

def get_full_id(fname):
    match = re.search(r'id_\d{8}-\d{2}', fname)
    return match.group() if match else ''

def get_base_id(fname):
    match = re.search(r'id_\d{8}', fname)
    return match.group() if match else ''

def search_similar(query_path, top_n=5):
    # Load precomputed data
    with open(FEATURES_FILE, 'rb') as f:
        data = pickle.load(f)  # [(filename, features, color)]

    query_fname = os.path.basename(query_path)
    query_features = extract_features(query_path)
    query_color = get_dominant_color(query_path)
    query_full_id = get_full_id(query_fname)
    query_base_id = get_base_id(query_fname)

    results = []

    for fname, feat, color in data:
        sim = cosine_similarity(query_features, feat)
        color_dist = color_distance(query_color, color)
        full_id = get_full_id(fname)
        base_id = get_base_id(fname)

        # Priority system
        if full_id == query_full_id:
            priority = 1
        elif base_id == query_base_id:
            priority = 2
        elif color_dist < 10:
            priority = 3
        else:
            priority = 4

        results.append((priority, -sim, color_dist, fname))  # -sim for descending sort

    results.sort()  # Sort by priority, then highest similarity, then color distance

    print(f"\nTop {top_n} prioritized similar products:")
    for i in range(min(top_n, len(results))):
        priority, neg_sim, color_dist, fname = results[i]
        print(f"{i+1}. {fname} — Priority: {priority} — Similarity: {-neg_sim:.4f} — ColorDist: {color_dist:.1f}")

def show_similar(query_img_path, top_n=5):
    # Load saved features: list of (filename, features, color)
    with open(FEATURES_FILE, 'rb') as f:
        data = pickle.load(f)

    query_fname = os.path.basename(query_img_path)
    query_features = extract_features(query_img_path)
    query_color = get_dominant_color(query_img_path)
    query_full_id = get_full_id(query_fname)
    query_base_id = get_base_id(query_fname)

    results = []
    for fname, feat, color in data:
        sim = cosine_similarity(query_features, feat)
        color_dist = color_distance(query_color, color)
        full_id = get_full_id(fname)
        base_id = get_base_id(fname)

        if full_id == query_full_id:
            priority = 1
        elif base_id == query_base_id:
            priority = 2
        elif color_dist < 10:
            priority = 3
        else:
            priority = 4

        results.append((priority, -sim, color_dist, fname))

    results.sort()
    top_matches = results[:top_n]

    # Plot images
    plt.figure(figsize=(16, 5), dpi=120)

    # Query image
    ax = plt.subplot(1, top_n + 1, 1)
    img = Image.open(query_img_path)
    plt.imshow(img)
    plt.title("Query Image", fontsize=10)
    plt.axis('off')

    for i, (_, neg_sim, color_dist, fname) in enumerate(top_matches):
        ax = plt.subplot(1, top_n + 1, i + 2)
        img_path = os.path.join(IMG_DIR, fname)
        img = Image.open(img_path)
        plt.imshow(img)
        plt.title(f"{fname[:20]}...\nSim: {-neg_sim:.2f}", fontsize=8)
        plt.axis('off')

    plt.tight_layout()
    plt.show()

# Run it
if __name__ == "__main__":
    if not os.path.exists(QUERY_IMAGE):
        print("Query image not found.")
    else:
        search_similar(QUERY_IMAGE)
        show_similar(QUERY_IMAGE)

