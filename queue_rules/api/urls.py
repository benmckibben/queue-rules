from django.urls import path

from . import views


urlpatterns = [
    path("rules/", views.RuleList.as_view(), name="rule-list"),
    path("rules/create/", views.CreateRule.as_view(), name="rule-create"),
    path("rules/<int:pk>/", views.RuleDetail.as_view(), name="rule-detail"),
    path("service_status/", views.ServiceStatus.as_view(), name="service-status"),
    path("logout/", views.Logout.as_view(), name="logout"),
    path("delete_account/", views.DeleteAccount.as_view(), name="delete-account"),
]
