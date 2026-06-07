import cv2
import numpy as np
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt

def get_top_colors(img_path, top_k=3):
    # Read image
    img = cv2.imread(img_path)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    # -------------------------
    # Step 1: Create better initial mask
    # -------------------------
    mask = np.full(img.shape[:2], 2, np.uint8)  # 2 = probable background

    # Mark borders as definite background
    border = 15
    mask[:border, :] = 0
    mask[-border:, :] = 0
    mask[:, :border] = 0
    mask[:, -border:] = 0

    # Mark central region as probable foreground
    h, w = img.shape[:2]
    mask[h//4:3*h//4, w//4:3*w//4] = 3

    # GrabCut
    bgdModel = np.zeros((1,65), np.float64)
    fgdModel = np.zeros((1,65), np.float64)
    cv2.grabCut(img, mask, None, bgdModel, fgdModel, 10, cv2.GC_INIT_WITH_MASK)

    # -------------------------
    # Step 2: Extract foreground
    # -------------------------
    mask2 = np.where((mask==2)|(mask==0), 0, 1).astype("uint8")
    fg_img = img * mask2[:, :, np.newaxis]

    # Morphological cleanup
    kernel = np.ones((3,3), np.uint8)
    mask2 = cv2.morphologyEx(mask2, cv2.MORPH_OPEN, kernel, iterations=2)

    # Extract pixels
    pixels = fg_img[mask2 == 1]
    if len(pixels) == 0:
        return None, fg_img

    # -------------------------
    # Step 3: KMeans clustering on foreground pixels
    # -------------------------
    kmeans = KMeans(n_clusters=top_k, random_state=42, n_init=10)
    kmeans.fit(pixels)

    colors = kmeans.cluster_centers_.astype(int)
    counts = np.bincount(kmeans.labels_)
    sorted_idx = np.argsort(-counts)

    top_colors = colors[sorted_idx]
    percentages = counts[sorted_idx] / sum(counts) * 100

    return list(zip(top_colors, percentages)), fg_img


# -------------------------
# Example usage
# -------------------------
if __name__ == "__main__":
    img_path = r"D:\Khushi Patel\Indus\Sem-7\SGP\data\deepfashion\img\WOMEN-Sweatshirts_Hoodies-id_00005200-01_7_additional.png"
    #"D:\Khushi Patel\Indus\Sem-7\SGP\data\deepfashion\img\WOMEN-Blouses_Shirts-id_00000104-02_4_full.png"
    #"D:\Khushi Patel\Indus\Sem-7\SGP\data\deepfashion\img\WOMEN-Cardigans-id_00000709-02_7_additional.png"
    #"D:\Khushi Patel\Indus\Sem-7\SGP\data\deepfashion\img\WOMEN-Dresses-id_00000819-04_4_full.png"
    #"D:\Khushi Patel\Indus\Sem-7\SGP\data\deepfashion\img\WOMEN-Rompers_Jumpsuits-id_00002545-04_4_full.png"
    #"D:\Khushi Patel\Indus\Sem-7\SGP\data\deepfashion\img\WOMEN-Rompers_Jumpsuits-id_00004340-03_2_side.png"
    #"D:\Khushi Patel\Indus\Sem-7\SGP\data\deepfashion\img\WOMEN-Skirts-id_00002588-02_1_front.png"
    #"D:\Khushi Patel\Indus\Sem-7\SGP\data\deepfashion\img\WOMEN-Sweaters-id_00007620-04_4_full.png"
    #"D:\Khushi Patel\Indus\Sem-7\SGP\data\deepfashion\img\WOMEN-Sweatshirts_Hoodies-id_00005200-01_7_additional.png"
    
    result, fg_img = get_top_colors(img_path, top_k=3)

    if result is None:
        print("No foreground detected.")
    else:
        print("Top-3 Colors (RGB) with percentages:")
        for i, (c, p) in enumerate(result, 1):
            print(f"{i}: {c}  ({p:.2f}%)")

        # Visualization
        plt.figure(figsize=(10,3))
        plt.subplot(1,4,1)
        plt.imshow(fg_img)
        plt.axis("off")
        plt.title("Foreground")

        for i, (c, p) in enumerate(result, 1):
            plt.subplot(1,4,i+1)
            plt.imshow(np.ones((100,100,3), dtype=np.uint8) * c)
            plt.axis("off")
            plt.title(f"{p:.1f}%")

        plt.tight_layout()
        plt.show()
