# Glammr
### AI-Based Image-Centric Product Discovery Platform

Glammr is a Pinterest-style fashion discovery web application that lets users search for products visually — by uploading an image — or through text queries. Powered by AI/ML feature extraction and backed by real-time shopping links via SerpAPI, it bridges the gap between inspiration and purchase.

---

## Features

- **Visual Search** — Upload a fashion image and instantly find visually similar products using ResNet50-based feature extraction and FAISS similarity indexing.
- **Text Search** — Keyword-based search with hybrid ranking that blends AI relevance and metadata filtering.
- **Inspiration Boards** — Create, manage, and organize saved products into personal boards (Pinterest-style), with soft-delete and undo support.
- **Masonry Feed** — Infinite-scrolling, responsive masonry grid displaying both the DeepFashion dataset images and user-uploaded content.
- **Shopping Links** — Clicking "Shop" on any product uploads it to Cloudinary and fetches real-time purchase links via SerpAPI (Google Lens integration).
- **User Authentication** — Signup, login, logout, and profile management with a dedicated `UserProfile` model.
- **Activity Feed** — Personal feed showing images saved to boards, tracked saves/uploads/likes per user.
- **Admin Control** — Django admin for managing users, uploads, boards, and content moderation.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11, Django 4.x, Django REST Framework |
| Frontend | HTML5, CSS3, JavaScript, Masonry.js |
| Database | SQLite (dev) / PostgreSQL or MySQL (prod) |
| AI / ML | TensorFlow / Keras — ResNet50, FAISS, NumPy, OpenCV |
| Image Storage | Cloudinary |
| Shopping API | SerpAPI (Google Shopping / Google Lens) |
| Auth | Django Auth (session-based) |
| Version Control | Git / GitHub |

---

## Project Structure

```
glammr/
├── backend/
│   └── config/
│       ├── settings.py        # Django settings
│       ├── urls.py            # Root URL configuration
│       ├── wsgi.py
│       └── asgi.py
├── api/                       # Core application logic
│   ├── models.py              # Upload, Board, Inspo, Image models
│   ├── views.py               # Feed, search, boards, shopping views
│   ├── urls.py                # API and page routes
│   ├── forms.py               # UploadForm, BoardForm
│   ├── extract_features.py    # ResNet50 feature extraction + FAISS indexing
│   └── migrations/
├── accounts/                  # User auth and profiles
│   ├── models.py              # UserProfile (extends Django User)
│   ├── views.py               # Signup, login, logout, settings
│   ├── signals.py             # Auto-create UserProfile on User creation
│   └── urls.py
├── frontend/
│   ├── templates/             # Django HTML templates
│   │   ├── index.html         # Main masonry feed
│   │   ├── auth.html          # Login / Signup
│   │   ├── boards.html        # Board listing
│   │   ├── view_board.html    # Individual board view
│   │   ├── image_view.html    # Product detail + shop link
│   │   ├── my_feed.html       # Personal activity feed
│   │   ├── upload.html        # Image upload form
│   │   ├── search_results.html
│   │   ├── search_results_image.html
│   │   └── myaccount.html
│   └── static/
│       ├── css/               # Per-page stylesheets
│       ├── js/                # index.js, image_view.js, masonry.pkgd.min.js, stats-updater.js
│       └── img/               # Default profile pic, logo, sample images
├── data/
│   └── deepfashion/
│       └── img/               # DeepFashion dataset images (12,000+)
├── media/
│   └── uploads/               # User-uploaded product images
├── dataset_features.pkl        # Precomputed ResNet50 feature vectors
├── dataset_features.index      # FAISS index for dataset images
├── upload_features.pkl         # Feature vectors for user uploads
├── upload_features.index       # FAISS index for user uploads
└── db.sqlite3
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- pip
- Git
- A Cloudinary account
- A SerpAPI key

### 1. Clone the repository

```bash
git clone https://github.com/khushi13124/glammr.git
cd glammr
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install django djangorestframework tensorflow faiss-cpu opencv-python-headless \
            cloudinary requests pillow tqdm matplotlib numpy scikit-learn
```

### 4. Configure secrets

Open `backend/config/settings.py` and replace the placeholder values:

```python
SECRET_KEY = 'your-secret-key-here'
```

Open `api/views.py` and update your API credentials:

```python
SERPAPI_KEY = "your-serpapi-key"

cloudinary.config(
    cloud_name="your-cloud-name",
    api_key="your-api-key",
    api_secret="your-api-secret"
)
```

### 5. Set up the DeepFashion dataset

Verify the dataset availabilty in the repository in data/ directory

### 6. Build the feature index

Run the feature extraction script to precompute ResNet50 vectors and build the FAISS index for all dataset images:

```bash
python api/extract_features.py
```

This generates `dataset_features.pkl` and `dataset_features.index` in the project root.

### 7. Apply migrations and create a superuser

```bash
cd backend
python manage.py migrate
python manage.py createsuperuser
```

### 8. Run the development server

```bash
python manage.py runserver
```

Open your browser at [http://127.0.0.1:8000/auth/](http://127.0.0.1:8000/auth/) to sign up and start exploring.

---

## Key URL Routes

| URL | Description |
|---|---|
| `/auth/` | Login / Signup |
| `/index/` | Main masonry feed |
| `/upload/` | Upload a product image |
| `/search/?q=` | Text-based search |
| `/search/?image=` | Image-based visual search |
| `/my-feed/` | Personal activity feed |
| `/my-boards/` | User's boards listing |
| `/view-board/<id>/` | Individual board view |
| `/image-view/` | Product detail + shopping links |
| `/purchase-search/<id>/` | Fetch SerpAPI shopping links |
| `/admin/` | Django admin panel |

---

## How Visual Search Works

1. User uploads a query image via the search interface.
2. The image is passed through a pre-trained **ResNet50** model (ImageNet weights); the `avg_pool` layer output produces a 2048-dimensional feature vector.
3. The vector is queried against a **FAISS** index built from all dataset images.
4. The top-*k* nearest neighbours (most visually similar products) are returned and displayed in the feed.

---

## Data Models

**Upload** — stores user-submitted product images with gender, category, and profile angle metadata.

**Board** — a named collection of saved inspirations per user, with soft-delete and privacy toggle.

**Inspo** — an individual item saved to a Board, storing the image URL, dimensions, title, and description.

**Image** — stores image URLs for general-purpose display (e.g., dataset references).

**UserProfile** — extends Django's built-in User with mobile number, profile picture, and privacy settings.

---

## Limitations

- Requires a stable internet connection for SerpAPI shopping links and Cloudinary uploads.
- AI inference speed depends on available CPU/GPU resources; a GPU is recommended for production.
- The DeepFashion dataset must be downloaded and indexed separately — it is not included in this repository.
- SerpAPI has rate limits; heavy usage may require a paid plan.
- Currently deployed in `DEBUG = True` mode; this must be changed before any public deployment.

---

## Future Enhancements

- Mobile application (React Native / Flutter)
- Real-time dataset updates via automated product crawlers
- Advanced analytics dashboard for user behaviour insights
- Multi-gesture / multi-modal search (combine text + image in a single query)
- Marketplace integrations (Flipkart, Amazon, Myntra affiliate APIs)
- Offline mode with cached recommendations

---

## Team

| Name | Enrollment |
|---|---|
| Disha Alagiya | IU2241230503 |
| Ishita Ahir | IU2241230512 |
| Khushi Patel | IU2241230525 |

**Guide:** Asst. Prof. Urvi Rabara, Assistant Professor, CSE Department  
**Institution:** Indus Institute of Technology and Engineering, Indus University, Ahmedabad — Nov 2025

---

## License

This project was developed as an academic submission for the Bachelor of Technology (Computer Science & Engineering) programme at Indus University. It is intended for educational purposes.
