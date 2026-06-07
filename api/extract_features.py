import os
import pickle
import faiss
import numpy as np
from tqdm import tqdm
import matplotlib.pyplot as plt
import math
import cv2
from pathlib import Path

from tensorflow.keras.applications.resnet50 import ResNet50, preprocess_input
from tensorflow.keras.preprocessing import image
from tensorflow.keras.models import Model

BASE_DIR = Path(__file__).resolve().parent.parent
DATASET_IMG_DIR = str(BASE_DIR / 'data' / 'deepfashion' / 'img')
UPLOAD_IMG_DIR  = str(BASE_DIR / 'media' / 'uploads')
SHAPE_ANN       = str(BASE_DIR / 'data' / 'deepfashion' / 'shape_ann' / 'train_ann_file.txt')
TEXTURE_ANN     = str(BASE_DIR / 'data' / 'deepfashion' / 'texture_ann' / 'train')
SEGM_ANN        = str(BASE_DIR / 'data' / 'deepfashion' / 'segm')
DATASET_FEATURES_FILE = str(BASE_DIR / 'dataset_features.pkl')
DATASET_INDEX_FILE    = str(BASE_DIR / 'dataset_features.index')
UPLOAD_FEATURES_FILE  = str(BASE_DIR / 'upload_features.pkl')
UPLOAD_INDEX_FILE     = str(BASE_DIR / 'upload_features.index')

base_model = ResNet50(weights='imagenet')
model = Model(inputs=base_model.input, outputs=base_model.get_layer('avg_pool').output)

def extract_features(img_path):
    try:
        img = image.load_img(img_path, target_size=(224, 224))
        x = image.img_to_array(img)
        x = np.expand_dims(x, axis=0)
        x = preprocess_input(x)
        feat = model.predict(x, verbose=0)
        return feat.flatten()
    except Exception as e:
        print(f"Error processing {img_path}: {e}")
        return None

def parse_shape_annotations(file_path):
    mapping = {}
    if not os.path.exists(file_path):
        return mapping
    with open(file_path, "r") as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) > 1:
                fname, labels = parts[0], parts[1:]
                mapping[fname] = labels
    return mapping

def parse_texture_annotations(folder):
    mapping = {}
    if not os.path.exists(folder):
        return mapping
    for fname in os.listdir(folder):
        fpath = os.path.join(folder, fname)
        if not os.path.isfile(fpath):
            continue
        with open(fpath, "r") as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) > 1:
                    img_name, labels = parts[0], parts[1:]
                    mapping.setdefault(img_name, []).extend(labels)
    return mapping

def build_index(image_dir, shape_ann, texture_ann, index_path, meta_path):
    features, paths, attrs = [], [], []

    print(f"Parsing annotations for {image_dir} ...")
    shape_map = parse_shape_annotations(shape_ann)
    texture_map = parse_texture_annotations(texture_ann)

    print(f"Extracting features from {image_dir} ...")
    for fname in tqdm(os.listdir(image_dir), desc=f"Processing {os.path.basename(image_dir)}"):
        fpath = os.path.join(image_dir, fname)
        if not os.path.isfile(fpath):
            continue

        feat = extract_features(fpath)
        if feat is None:
            continue

        shape_labels = shape_map.get(fname, [])
        texture_labels = texture_map.get(fname, [])
        all_labels = shape_labels + texture_labels

        features.append(feat)
        paths.append(fpath)
        attrs.append(all_labels)

    if not features:
        print(f"No features extracted from {image_dir}")
        return

    features = np.array(features).astype("float32")

    print(f"Saving FAISS index → {index_path}")
    d = features.shape[1]
    index = faiss.IndexFlatL2(d)
    index.add(features)
    faiss.write_index(index, index_path)

    print(f"Saving metadata → {meta_path}")
    with open(meta_path, "wb") as f:
        pickle.dump({"paths": paths, "attrs": attrs}, f)

    print(f"Done: {len(paths)} images processed from {image_dir}")

def append_to_index(img_dir, index_path, meta_path):
    if not os.path.exists(index_path) or not os.path.exists(meta_path):
        build_index(img_dir, SHAPE_ANN, TEXTURE_ANN, index_path, meta_path)
        return

    index = faiss.read_index(index_path)
    with open(meta_path, "rb") as f:
        meta = pickle.load(f)

    existing_paths = set(meta["paths"])
    new_features, new_paths, new_attrs = [], [], []

    for fname in os.listdir(img_dir):
        fpath = os.path.join(img_dir, fname)
        if not os.path.isfile(fpath) or fpath in existing_paths:
            continue

        feat = extract_features(fpath)
        if feat is None:
            continue

        new_features.append(feat)
        new_paths.append(fpath)
        new_attrs.append([])

    if not new_features:
        print("No new uploads to add.")
        return

    new_features = np.array(new_features).astype("float32")
    index.add(new_features)

    meta["paths"].extend(new_paths)
    meta["attrs"].extend(new_attrs)

    faiss.write_index(index, index_path)
    with open(meta_path, "wb") as f:
        pickle.dump(meta, f)

    print(f"Added {len(new_paths)} new images to index.")

def search_similar(query_img_path, index_file, meta_file, top_k=5):
    if not os.path.exists(index_file) or not os.path.exists(meta_file):
        return [], {}

    index = faiss.read_index(index_file)
    with open(meta_file, 'rb') as f:
        meta = pickle.load(f)

    query_feat = extract_features(query_img_path)
    if query_feat is None:
        return [], meta
    query_feat = query_feat.reshape(1, -1).astype('float32')

    if top_k is None:
        top_k = index.ntotal
    top_k = max(1, min(top_k, index.ntotal))

    distances, indices = index.search(query_feat, top_k)
    distances = distances.flatten()
    indices = indices.flatten()

    results = []
    for i, idx in enumerate(indices):
        results.append({'path': meta['paths'][idx], 'score': float(distances[i])})

    print("Matches found:", len(results))       #Test

    return results, meta

def show_results(query_img_path, results, meta):
    query_img = cv2.imread(query_img_path)
    query_img = cv2.cvtColor(query_img, cv2.COLOR_BGR2RGB)

    total = len(results) + 1
    cols = min(5, total)
    rows = math.ceil(total / cols)

    plt.figure(figsize=(4 * cols, 4 * rows))

    plt.subplot(rows, cols, 1)
    plt.imshow(query_img)
    plt.title("Query", fontsize=12)
    plt.axis("off")

    for i, res in enumerate(results, start=2):
        img = cv2.imread(res["path"])
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        fname = os.path.basename(res["path"])

        labels = []
        if "attrs" in meta and res["path"] in meta["paths"]:
            idx = meta["paths"].index(res["path"])

        plt.subplot(rows, cols, i)
        plt.imshow(img)
        plt.title(f"{fname}\nScore: {res['score']:.2f}", fontsize=9)
        plt.axis("off")

    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    if not os.path.exists(DATASET_INDEX_FILE) or not os.path.exists(DATASET_FEATURES_FILE):
        build_index(DATASET_IMG_DIR, SHAPE_ANN, TEXTURE_ANN, DATASET_INDEX_FILE, DATASET_FEATURES_FILE)

    append_to_index(UPLOAD_IMG_DIR, UPLOAD_INDEX_FILE, UPLOAD_FEATURES_FILE)
    
    image_name = 'add-your-test-image-name-here'
    test_img = str(BASE_DIR / 'data' / 'deepfashion' / 'img'/ image_name)
    results, dataset_meta = search_similar(test_img, DATASET_INDEX_FILE, DATASET_FEATURES_FILE, top_k=10)

    print("\nTop-most similar images:")
    for r in results:
        print(f"{r['path']} (score: {r['score']:.4f})")

    show_results(test_img, results, dataset_meta)
