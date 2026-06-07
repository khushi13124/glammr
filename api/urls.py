from django.urls import path
from . import views
from .views import masonry_view, upload_view, my_feed_view, my_boards_view, get_boards, purchase_search_view, test_login

urlpatterns = [
    # Main views
    path('index/', views.masonry_view, name='index'),
    path('upload/', views.upload_view, name='upload'),
    path('my-feed/', views.my_feed_view, name='my_feed'),
    
    # Board management
    path('create-board/', views.create_board_view, name='create_board'),
    path('save-to-board/', views.save_to_board_view, name='save_to_board'),
    path('api/get-boards/', views.get_boards, name='get_boards'),
    path('my-boards/', views.my_boards_view, name='my_boards'),
    path('view-board/<int:board_id>/', views.view_board_view, name='view_board'),
    path('get-board-images/<int:board_id>/', views.get_board_images, name='get_board_images'),
    path('delete-board/', views.delete_board_view, name='delete_board'),
    path('undo-delete-board/', views.undo_delete_board_view, name='undo_delete_board'),
    
    # Image management
    path('unsave-image/', views.unsave_image_view, name='unsave_image'),
    path('undo-unsave-image/', views.undo_unsave_image_view, name='undo_unsave_image'),
    path('image-detail/', views.get_image_detail, name='get_image_detail'),
    path('image-view/', views.image_view_page, name='image_view'),
    
    # Stats API endpoints
    path('api/get-stats/saves/', views.get_saves_count, name='get_saves_count'),
    path('api/get-stats/uploads/', views.get_uploads_count, name='get_uploads_count'),
    path('api/get-stats/boards/', views.get_boards_count, name='get_boards_count'),
    path('api/get-stats/likes/', views.get_likes_count, name='get_likes_count'),
    path('api/get-stats/all/', views.get_all_stats, name='get_all_stats'),

    #Search
    path("search/", views.hybrid_search, name="hybrid_search"),

    #API Integration
    path("purchase-search/<int:image_id>/", views.purchase_search_view, name="purchase_search"),
    # urls.py
    path('test-login/', views.test_login, name='test_login')

]