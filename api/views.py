import os
import random
import json
import logging
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db.models import Count
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .forms import UploadForm, BoardForm
from .models import Upload, Board, Inspo, Image
from .extract_features import search_similar, DATASET_INDEX_FILE, DATASET_FEATURES_FILE, UPLOAD_FEATURES_FILE, UPLOAD_INDEX_FILE
from django.db.models import Count, Q
from django.template.loader import render_to_string
import cloudinary.uploader
import requests
from django.http import HttpResponse
import os
from django.conf import settings

SERPAPI_KEY = os.environ.get('SERPAPI_KEY')

cloudinary.config(
    cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
    api_key=os.environ.get('CLOUDINARY_API_KEY'),
    api_secret=os.environ.get('CLOUDINARY_API_SECRET')
)

logger = logging.getLogger(__name__)
DATASET_ID_START = 1000001
DATASET_FILES = sorted([
    f for f in os.listdir(settings.DEEPFASHION_IMAGE_ROOT)
    if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.gif'))
])
DATASET_ID_MAP = {DATASET_ID_START + idx: fname for idx, fname in enumerate(DATASET_FILES)}

# -------------------------------
# Masonry / Feed View
# -------------------------------
@login_required(login_url='/auth/')
def masonry_view(request):
    dataset_images = [
        {
            'type': 'dataset',
            'path': settings.DEEPFASHION_IMAGE_URL + filename,
            'id': DATASET_ID_START + idx,
            'filename': filename,
            'dataset_id': DATASET_ID_START + idx
        }
        for idx, filename in enumerate(DATASET_FILES)
    ]

    uploaded_images = Upload.objects.all()
    uploaded_image_data = [
        {
            'type': 'upload',
            'path': upload.image.url,
            'id': upload.id
        } for upload in uploaded_images
    ]

    all_images = dataset_images + uploaded_image_data
    random.shuffle(all_images)

    boards = (
        Board.objects
        .filter(user=request.user, is_deleted=False)
        .annotate(non_deleted_count=Count("inspos", filter=Q(inspos__is_deleted=False)))
    )

    return render(request, 'index.html', {'image_urls': all_images, 'boards': boards})


@login_required(login_url='/auth/')
def upload_view(request):
    if request.method == 'POST':
        form = UploadForm(request.POST, request.FILES)
        if form.is_valid():
            upload = form.save(commit=False)
            upload.user = request.user
            upload.save()

            os.makedirs(os.path.join(settings.MEDIA_ROOT, 'uploads'), exist_ok=True)

            ext = os.path.splitext(upload.image.name)[1]
            new_filename = f"{upload.gender}-{upload.category}-{upload.profile}-id-{upload.id}{ext}"
            old_path = upload.image.path
            new_path = os.path.join(settings.MEDIA_ROOT, 'uploads', new_filename)
            os.rename(old_path, new_path)

            upload.image.name = f"uploads/{new_filename}"
            upload.save()

            return redirect('index')
    else:
        form = UploadForm()
    return render(request, 'upload.html', {'form': form})


@login_required(login_url='/auth/')
def my_feed_view(request):
    uploaded_images = Upload.objects.filter(user=request.user).order_by('-timestamp')
    return render(request, 'my_feed.html', {'images': uploaded_images})

@csrf_exempt
@login_required(login_url='/auth/')
def create_board_view(request):
    if request.method == 'POST':
        # Handle both form data and JSON data
        if request.content_type == 'application/json':
            data = json.loads(request.body)
            board_name = data.get('name', '').strip()
        else:
            board_name = request.POST.get('name', '').strip()
       
        # Validate board name
        if not board_name:
            return JsonResponse({'status': 'error', 'message': 'Board name is required'}, status=400)
       
        if len(board_name) > 100:
            return JsonResponse({'status': 'error', 'message': 'Board name must be 100 characters or less'}, status=400)
       
        # Check if user already has a board with this name
        if Board.objects.filter(user=request.user, name=board_name, is_deleted=False).exists():
            return JsonResponse({'status': 'error', 'message': 'You already have a board with this name'}, status=400)
       
        try:
            # Create the board
            board = Board.objects.create(
                user=request.user,
                name=board_name
            )
           
            # Invalidate cache
            invalidate_user_cache(request.user.id, 'boards')
           
            return JsonResponse({
                'status': 'success',
                'board_id': board.id,
                'board_name': board.name,
                'message': f'Board "{board.name}" created successfully!'
            })
           
        except Exception as e:
            logger.error(f"Error creating board for user {request.user.id}: {str(e)}")
            return JsonResponse({'status': 'error', 'message': 'Failed to create board'}, status=500)
   
    return JsonResponse({'status': 'error', 'message': 'Only POST method allowed'}, status=405)

@csrf_exempt
@login_required(login_url='/auth/')
def save_to_board_view(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        image_url = data.get('image_url')
        board_id = data.get('board_id')

        try:
            board = Board.objects.get(id=board_id, user=request.user, is_deleted=False)
           
            # Check if image already exists in this board
            if Inspo.objects.filter(board=board, image_url=image_url, is_deleted=False).exists():
                return JsonResponse({'status': 'error', 'message': 'Image already saved to this board'})
           
            inspo = Inspo.objects.create(board=board, image_url=image_url)

            # Also store in "My Saves" if it's not already the current board
            default_board = Board.get_default_board(request.user)
            default_board_count = None
           
            if board.id != default_board.id:
                # Check if already in My Saves
                if not Inspo.objects.filter(board=default_board, image_url=image_url, is_deleted=False).exists():
                    Inspo.objects.create(board=default_board, image_url=image_url)
               
                # Get updated count for My Saves
                default_board_count = default_board.inspos.filter(is_deleted=False).count()

            # Get updated count for this board
            board_image_count = board.inspos.filter(is_deleted=False).count()

            # Invalidate cache
            invalidate_user_cache(request.user.id, 'saves')

            response_data = {
                'status': 'success',
                'board_id': board.id,
                'board_name': board.name,
                'image_url': inspo.image_url,
                'inspo_id': inspo.id,
                'board_image_count': board_image_count,
                'default_board_id': default_board.id
            }
           
            # Include default board count if it was updated
            if default_board_count is not None:
                response_data['default_board_count'] = default_board_count
               
            return JsonResponse(response_data)
           
        except Board.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Board not found'})
        except Exception as e:
            logger.error(f"Error saving to board for user {request.user.id}: {str(e)}")
            return JsonResponse({'status': 'error', 'message': 'Failed to save to board'}, status=500)
           
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

@csrf_exempt
@login_required(login_url='/auth/')
def my_boards_view(request):
    boards = (
        Board.objects
        .filter(user=request.user, is_deleted=False)
        .prefetch_related('inspos')
    )

    # Attach only the latest 4 images for preview
    for b in boards:
        b.preview_inspos = list(
            b.inspos.filter(is_deleted=False).order_by('-saved_at')[:4]
        )

    return render(request, 'boards.html', {'boards': boards})

@csrf_exempt
@login_required(login_url='/auth/')
def view_board_view(request, board_id):
    board = get_object_or_404(Board, id=board_id, user=request.user, is_deleted=False)
    images = board.inspos.filter(is_deleted=False).order_by('-saved_at')
   
    # Get dataset images for display below saved images
    image_dir = settings.DEEPFASHION_IMAGE_ROOT
    dataset_images = []
   
    try:
        for filename in os.listdir(image_dir):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.gif')):
                dataset_images.append({
                    'type': 'dataset',
                    'url': settings.DEEPFASHION_IMAGE_URL + filename,
                    'filename': filename
                })
       
        # Shuffle for variety
        random.shuffle(dataset_images)
        # Limit to reasonable number for performance
        dataset_images = dataset_images[:100]
       
    except Exception as e:
        logger.error(f"Error loading dataset images: {str(e)}")
        dataset_images = []
   
    # Get all user boards for any remaining dropdowns
    user_boards = Board.objects.filter(user=request.user, is_deleted=False).order_by('name')
   
    return render(request, 'view_board.html', {
        'board': board,
        'images': images,
        'dataset_images': dataset_images,
        'user_boards': user_boards
    })


@login_required(login_url='/auth/')
def unsave_image_view(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        inspo_id = data.get('inspo_id')

        inspo = get_object_or_404(Inspo, id=inspo_id, board__user=request.user)

        # Find all inspos across ALL boards with same image_url
        related_inspos = Inspo.objects.filter(
            board__user=request.user,
            image_url=inspo.image_url,
            is_deleted=False
        )

        # Mark all as deleted
        related_inspos.update(is_deleted=True)

        # Count images left per board (for live sync update)
        affected_boards = (
            Board.objects.filter(inspos__image_url=inspo.image_url, user=request.user)
            .distinct()
            .values('id')
        )

        board_counts = []
        for b in Board.objects.filter(id__in=[x['id'] for x in affected_boards]):
            board_counts.append({
                "board_id": b.id,
                "count": b.inspos.filter(is_deleted=False).count()
            })

        # Invalidate cache
        invalidate_user_cache(request.user.id, 'saves')

        return JsonResponse({
            "status": "success",
            "inspo_id": inspo_id,
            "affected_boards": board_counts,
            "image_url": inspo.image_url
        })

    return JsonResponse({"status": "error", "message": "Invalid request"})

@csrf_exempt
@login_required(login_url='/auth/')
def undo_unsave_image_view(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        inspo_id = data.get('inspo_id')
       
        inspo = get_object_or_404(Inspo, id=inspo_id, board__user=request.user)
       
        # Find all related inspos that were deleted at the same time
        related_inspos = Inspo.objects.filter(
            board__user=request.user,
            image_url=inspo.image_url,
            is_deleted=True
        )
       
        # Restore all
        related_inspos.update(is_deleted=False)
       
        # Get updated counts
        affected_boards = (
            Board.objects.filter(inspos__image_url=inspo.image_url, user=request.user)
            .distinct()
            .values('id')
        )

        board_counts = []
        for b in Board.objects.filter(id__in=[x['id'] for x in affected_boards]):
            board_counts.append({
                "board_id": b.id,
                "count": b.inspos.filter(is_deleted=False).count()
            })

        # Invalidate cache
        invalidate_user_cache(request.user.id, 'saves')
       
        return JsonResponse({
            "status": "success",
            "affected_boards": board_counts
        })
    return JsonResponse({"status": "error", "message": "Invalid request"})

@csrf_exempt
@login_required(login_url='/auth/')
def delete_board_view(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        board_id = data.get('board_id')
        board = get_object_or_404(Board, id=board_id, user=request.user)
        if board.name == "My Saves":
            return JsonResponse({"status": "error", "message": "Cannot delete My Saves"})
        board.is_deleted = True
        board.save(update_fields=['is_deleted'])
       
        # Invalidate cache
        invalidate_user_cache(request.user.id, 'boards')
       
        return JsonResponse({"status": "success", "board_id": board_id, "board_name": board.name})
    return JsonResponse({"status": "error", "message": "Invalid request"})


@login_required(login_url='/auth/')
def undo_delete_board_view(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        board_id = data.get('board_id')
        board = get_object_or_404(Board, id=board_id, user=request.user)
        board.is_deleted = False
        board.save(update_fields=['is_deleted'])
       
        # Invalidate cache
        invalidate_user_cache(request.user.id, 'boards')
       
        return JsonResponse({
            "status": "success",
            "board_name": board.name,
            "board_image_count": board.inspos.filter(is_deleted=False).count()
        })
    return JsonResponse({"status": "error", "message": "Invalid request"})


@login_required(login_url='/auth/')
def get_image_detail(request):
    image_url = request.GET.get('image_url')
    page = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('page_size', 50))

    boards = [{'id': b.id, 'name': b.name, 'count': b.image_count}
              for b in Board.objects.filter(user=request.user, is_deleted=False)]

    similar_images = []

    img_path = None
    if image_url:
        if image_url.startswith(settings.MEDIA_URL):
            img_path = os.path.join(settings.MEDIA_ROOT, image_url[len(settings.MEDIA_URL):])
        elif image_url.startswith(settings.DEEPFASHION_IMAGE_URL):
            img_path = os.path.join(settings.DEEPFASHION_IMAGE_ROOT, os.path.basename(image_url))

        if img_path and os.path.exists(img_path):
            results, meta = search_similar(img_path, DATASET_INDEX_FILE, DATASET_FEATURES_FILE, top_k=None)
            # Convert to URLs
            for r in results:
                path, score = r['path'], r['score']
                if path.startswith(settings.DEEPFASHION_IMAGE_ROOT):
                    url = settings.DEEPFASHION_IMAGE_URL + os.path.basename(path)
                elif path.startswith(settings.MEDIA_ROOT):
                    url = settings.MEDIA_URL + os.path.basename(path)
                else:
                    url = path
                if url != image_url:
                    similar_images.append(url)

    # Pagination
    paginator = Paginator(similar_images, page_size)
    page_obj = paginator.get_page(page)

    return JsonResponse({
        'status': 'success',
        'url': image_url,
        'boards': boards,
        'similar_images': list(page_obj),
        'has_next': page_obj.has_next(),
        'next_page': page_obj.next_page_number() if page_obj.has_next() else None
    })


@login_required(login_url='/auth/')
def image_view(request):
    """
    Render fullscreen view using ?image_url=... instead of ID
    """
    image_url = request.GET.get('image_url')
    return render(request, 'image_view.html', {'image_url': image_url})


# Helper: return board images as JSON
@login_required(login_url='/auth/')
def get_board_images(request, board_id):
    board = get_object_or_404(Board, id=board_id, user=request.user, is_deleted=False)
    images = list(board.inspos.filter(is_deleted=False).order_by('-saved_at')
                  .values('id', 'image_url', 'saved_at'))
    return JsonResponse({"status": "success", "images": images})


@login_required(login_url='/auth/')
def image_view_page(request):
    return render(request, 'image_view.html')


# Stats API Views
@login_required
@require_http_methods(["GET"])
def get_saves_count(request):
    """Get the current number of saves for the user"""
    try:
        cache_key = f"user_saves_count_{request.user.id}"
        saves_count = cache.get(cache_key)
       
        if saves_count is None:
            saves_count = get_user_saves_count(request.user)
            cache.set(cache_key, saves_count, 300)
       
        return JsonResponse({
            'status': 'success',
            'count': saves_count
        })
       
    except Exception as e:
        logger.error(f"Error getting saves count for user {request.user.id}: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': 'Failed to get saves count'
        }, status=500)


@login_required
@require_http_methods(["GET"])
def get_uploads_count(request):
    """Get the current number of uploads for the user"""
    try:
        cache_key = f"user_uploads_count_{request.user.id}"
        uploads_count = cache.get(cache_key)
       
        if uploads_count is None:
            uploads_count = get_user_uploads_count(request.user)
            cache.set(cache_key, uploads_count, 300)
       
        return JsonResponse({
            'status': 'success',
            'count': uploads_count
        })
       
    except Exception as e:
        logger.error(f"Error getting uploads count for user {request.user.id}: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': 'Failed to get uploads count'
        }, status=500)


@login_required
@require_http_methods(["GET"])
def get_boards_count(request):
    """Get the current number of boards for the user"""
    try:
        cache_key = f"user_boards_count_{request.user.id}"
        boards_count = cache.get(cache_key)
       
        if boards_count is None:
            boards_count = get_user_boards_count(request.user)
            cache.set(cache_key, boards_count, 300)
       
        return JsonResponse({
            'status': 'success',
            'count': boards_count
        })
       
    except Exception as e:
        logger.error(f"Error getting boards count for user {request.user.id}: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': 'Failed to get boards count'
        }, status=500)


@login_required
@require_http_methods(["GET"])
def get_likes_count(request):
    """Get the current number of likes for the user"""
    try:
        cache_key = f"user_likes_count_{request.user.id}"
        likes_count = cache.get(cache_key)
       
        if likes_count is None:
            likes_count = get_user_likes_count(request.user)
            cache.set(cache_key, likes_count, 300)
       
        return JsonResponse({
            'status': 'success',
            'count': likes_count
        })
       
    except Exception as e:
        logger.error(f"Error getting likes count for user {request.user.id}: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': 'Failed to get likes count'
        }, status=500)


@login_required
@require_http_methods(["GET"])
def get_all_stats(request):
    """Get all stats for the user in one request"""
    try:
        user_id = request.user.id
       
        # Get all stats with caching
        stats = {
            'saves': cache.get_or_set(
                f"user_saves_count_{user_id}",
                lambda: get_user_saves_count(request.user),
                300
            ),
            'uploads': cache.get_or_set(
                f"user_uploads_count_{user_id}",
                lambda: get_user_uploads_count(request.user),
                300
            ),
            'boards': cache.get_or_set(
                f"user_boards_count_{user_id}",
                lambda: get_user_boards_count(request.user),
                300
            ),
            'likes': cache.get_or_set(
                f"user_likes_count_{user_id}",
                lambda: get_user_likes_count(request.user),
                300
            )
        }
       
        return JsonResponse({
            'status': 'success',
            'stats': stats
        })
       
    except Exception as e:
        logger.error(f"Error getting all stats for user {request.user.id}: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': 'Failed to get stats'
        }, status=500)


# Helper functions to calculate actual counts
def get_user_saves_count(user):
    """Calculate user's saves count (items in default 'My Saves' board)"""
    try:
        from .models import Board
        default_board = Board.get_default_board(user)
        return default_board.inspos.filter(is_deleted=False).count()
    except Exception as e:
        logger.error(f"Error calculating saves count for user {user.id}: {str(e)}")
        return 0


def get_user_uploads_count(user):
    """Calculate user's uploads count"""
    try:
        return Upload.objects.filter(user=user).count()
    except Exception as e:
        logger.error(f"Error calculating uploads count for user {user.id}: {str(e)}")
        return 0


def get_user_boards_count(user):
    """Calculate user's boards count"""
    try:
        return Board.objects.filter(user=user, is_deleted=False).count()
    except Exception as e:
        logger.error(f"Error calculating boards count for user {user.id}: {str(e)}")
        return 0


def get_user_likes_count(user):
    """Calculate user's likes count"""
    try:
        # If you have a likes system, implement it here
        # For now, returning 0 as placeholder
        return 0
    except Exception as e:
        logger.error(f"Error calculating likes count for user {user.id}: {str(e)}")
        return 0


def invalidate_user_cache(user_id, stat_type):
    """Helper function to invalidate user's stats cache"""
    cache_key = f"user_{stat_type}_count_{user_id}"
    cache.delete(cache_key)


# Signal handlers to invalidate cache when data changes
@receiver(post_save, sender=Board)
@receiver(post_delete, sender=Board)
def invalidate_boards_cache(sender, instance, **kwargs):
    """Invalidate boards cache when a board is created or deleted"""
    if hasattr(instance, 'user') and instance.user:
        invalidate_user_cache(instance.user.id, 'boards')


@receiver(post_save, sender=Upload)
@receiver(post_delete, sender=Upload)
def invalidate_uploads_cache(sender, instance, **kwargs):
    """Invalidate uploads cache when an upload is created or deleted"""
    if hasattr(instance, 'user') and instance.user:
        invalidate_user_cache(instance.user.id, 'uploads')


@receiver(post_save, sender=Inspo)
@receiver(post_delete, sender=Inspo)
def invalidate_saves_cache(sender, instance, **kwargs):
    """Invalidate saves cache when an inspo is created or deleted"""
    if hasattr(instance, 'board') and instance.board and hasattr(instance.board, 'user'):
        invalidate_user_cache(instance.board.user.id, 'saves')


@csrf_exempt
def hybrid_search(request):
    """
    Handles both text-based and image-based search.
    - POST → can contain query (q) and/or image
    - GET → works for query only (?q=...)
    """
    results = []

    # --- POST (text and/or image search) ---
    if request.method == "POST":
        query = (request.POST.get("q") or "").strip()
        image_file = request.FILES.get("image")

        # --- TEXT SEARCH ---
        if query:
            dataset_dir = settings.DEEPFASHION_IMAGE_ROOT
            all_images = []
            for root, _, files in os.walk(dataset_dir):
                for f in files:
                    if f.lower().endswith((".jpg", ".png", ".jpeg")):
                        if query.lower() in f.lower():
                            rel_path = os.path.relpath(os.path.join(root, f), dataset_dir)
                            all_images.append({
                                "title": f,
                                "image": (settings.DEEPFASHION_IMAGE_URL + rel_path.replace("\\", "/"))
                            })
            results = all_images

            # return full page if text search (not AJAX)
            if not image_file:
                return render(request, "search_results.html", {"query": query, "results": results})

        # --- IMAGE SEARCH ---
        if image_file:
            tmp_dir = os.path.join(settings.MEDIA_ROOT, "temp")
            os.makedirs(tmp_dir, exist_ok=True)
            tmp_path = os.path.join(tmp_dir, image_file.name)

            with open(tmp_path, "wb") as out:
                for chunk in image_file.chunks():
                    out.write(chunk)

            # ✅ Run search on dataset index
            matches_dataset, _ = search_similar(
                tmp_path,
                DATASET_INDEX_FILE,
                DATASET_FEATURES_FILE,
                top_k=None
            )

            # ✅ Run search on uploads index
            matches_uploads, _ = search_similar(
                tmp_path,
                UPLOAD_INDEX_FILE,
                UPLOAD_FEATURES_FILE,
                top_k=None
            )

            # ✅ Merge results
            matches = matches_dataset + matches_uploads

            results = []
            for m in sorted(matches, key=lambda x: x["score"]):
                abs_path = m["path"]

                # figure out if it's dataset or upload
                if abs_path.startswith(settings.DEEPFASHION_IMAGE_ROOT):
                    rel_path = os.path.relpath(abs_path, settings.DEEPFASHION_IMAGE_ROOT)
                    url = settings.DEEPFASHION_IMAGE_URL + rel_path.replace("\\", "/")
                else:  # must be from uploads
                    rel_path = os.path.relpath(abs_path, os.path.join(settings.MEDIA_ROOT, "uploads"))
                    url = settings.MEDIA_URL + "uploads/" + rel_path.replace("\\", "/")

                results.append({
                    "title": os.path.basename(abs_path),
                    "image": url
                })

            return render(request, "search_results_image.html", {"results": results})


    # --- GET (simple query, e.g. /search/?q=...) ---
    if request.method == "GET":
        query = request.GET.get("q", "").strip()
        if query:
            dataset_dir = settings.DEEPFASHION_IMAGE_ROOT
            all_images = []
            for root, _, files in os.walk(dataset_dir):
                for f in files:
                    if f.lower().endswith((".jpg", ".png", ".jpeg")):
                        if query.lower() in f.lower():
                            rel_path = os.path.relpath(os.path.join(root, f), dataset_dir)
                            all_images.append({
                                "title": f,
                                "image": (settings.DEEPFASHION_IMAGE_URL + rel_path.replace("\\", "/"))
                            })
            results = all_images

        return render(request, "search_results.html", {"query": query, "results": results})

def get_boards(request):
    if not request.user.is_authenticated:
        return JsonResponse({"status": "error", "message": "Not authenticated"}, status=403)

    boards = Board.objects.filter(user=request.user, is_deleted=False)

    result = []
    for b in boards:
        result.append({
            "id": b.id,
            "name": b.name,
            "non_deleted_count": b.inspos.filter(is_deleted=False).count()  # ✅ use inspos
        })

    return JsonResponse({"status": "success", "boards": result})

@login_required(login_url='/auth/')
def purchase_search_view(request, image_id):
    try:
        image_id = int(image_id)

        if image_id in DATASET_ID_MAP:
            # Dataset image
            filename = DATASET_ID_MAP[image_id]
            image_url = os.path.join(settings.DEEPFASHION_IMAGE_URL, filename)
            local_path = os.path.join(settings.DEEPFASHION_IMAGE_ROOT, filename)
        else:
            # Uploaded image
            upload = Upload.objects.get(id=image_id)
            image_url = upload.image.url
            local_path = upload.image.path

        # Upload to Cloudinary if not already URL
        if image_url.startswith(settings.MEDIA_URL) or image_id in DATASET_ID_MAP:
            upload_result = cloudinary.uploader.upload(local_path)
            image_url = upload_result["secure_url"]

        # Call SerpAPI Google Lens
        params = {
            "engine": "google_lens",
            "url": image_url,
            "api_key": SERPAPI_KEY
        }
        response = requests.get("https://serpapi.com/search", params=params)
        if response.status_code == 200:
            data = response.json()
            google_lens_link = data.get("search_metadata", {}).get("google_lens_url")
            if google_lens_link:
                return redirect(google_lens_link)

    except Upload.DoesNotExist:
        logger.error(f"Uploaded image {image_id} not found")
    except Exception as e:
        logger.error(f"Error in purchase_search_view: {str(e)}")

    # Fallback if anything goes wrong
    return redirect("/")

@login_required
def test_login(request):
    return HttpResponse("You are logged in!")