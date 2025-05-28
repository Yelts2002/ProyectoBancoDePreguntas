from django.urls import path
from . import views

urlpatterns = [
    # URLs para Universidad
    path('universidades/', views.UniversidadListView.as_view(), name='universidad-list'),
    path('universidad/nueva/', views.UniversidadCreateView.as_view(), name='universidad-create'),
    path('universidad/<int:pk>/editar/', views.UniversidadUpdateView.as_view(), name='universidad-update'),
    path('universidad/<int:pk>/eliminar/', views.UniversidadDeleteView.as_view(), name='universidad-delete'),
    
    # URLs para cursos
    path('cursos/', views.CursoListView.as_view(), name='curso-list'),
    path('curso/nueva/', views.CursoCreateView.as_view(), name='curso-create'),
    path('curso/<int:pk>/editar/', views.CursoUpdateView.as_view(), name='curso-update'),
    path('curso/<int:pk>/eliminar/', views.CursoDeleteView.as_view(), name='curso-delete'),

    # URLs para temas
    path('temas/', views.TemaListView.as_view(), name='tema-list'),
    path('tema/nuevo/', views.TemaCreateView.as_view(), name='tema-create'),
    path('tema/<int:pk>/editar/', views.TemaUpdateView.as_view(), name='tema-update'),
    path('tema/<int:pk>/eliminar/', views.TemaDeleteView.as_view(), name='tema-delete'),

    # URLs para Preguntas
    path('preguntas/', views.pregunta_list, name='pregunta-list'),
    path('pregunta/nueva/', views.pregunta_create, name='pregunta-create'),
    path('pregunta/<int:pk>/vista-previa/', views.vista_previa, name='vista-previa'),
    path('pregunta/<int:pk>/eliminar/', views.pregunta_delete, name='pregunta-delete'),
    path('pregunta/<int:pk>/editar/', views.pregunta_update, name='pregunta-update'),
    path('descargar-preguntas/', views.descargar_preguntas, name='descargar-preguntas'),
    path('vista_previa/<int:pk>/', views.vista_previa, name='vista_previa'),
    path('pregunta/<int:pk>/vista-previa/', views.vista_previa, name='vista-previa'),
    path('preguntas/todas/', views.todas_las_preguntas, name='todas_las_preguntas'),

    # URL para Generar Examen (solo administrador)
    path('examen/generar/', views.generar_examen, name='generar-examen'),
    path('examen/generar/', views.generar_examen, name='generar_examen'),

    # URLs para Logins
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('admin/dashboard/', views.admin_dashboard, name='admin-dashboard'),
    path('export-preguntas-recientes/', views.export_preguntas_recientes, name='export-preguntas-recientes'),
    path('admin/toggle-user-status/<str:username>/', views.toggle_user_status, name='toggle-user-status'),
    path('preguntas/supervisor/', views.pregunta_list_supervisor, name='pregunta_list_supervisor'),
    path('admin/users/<str:username>/change-role/', views.change_user_role, name='change-user-role'),

    # URL para AJAX
    path('ajax/load-cursos/', views.load_cursos, name='load_cursos'),
    path('ajax/load-temas/',  views.load_temas,  name='load_temas'),

]