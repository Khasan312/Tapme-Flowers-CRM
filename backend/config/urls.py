from django.contrib import admin
from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.permissions import IsAuthenticated

from config.health import health
from tapme.accounts.api import CsrfView, LoginView, LogoutView, MeView, PasswordView
from tapme.businesses.api import BusinessListView
from tapme.businesses.points_api import (
    PointArchiveView,
    PointDetailView,
    PointsView,
    StaffPointsView,
)
from tapme.businesses.settings_api import ResetStaffView, SettingsView, StaffDetailView, StaffView
from tapme.catalog.api import ProductDetailView, ProductListView, ProductPhotoView
from tapme.customers.api import CustomerListView
from tapme.customers.directory_api import DirectoryView
from tapme.customers.profile_api import ActivityView, CustomerDetailView
from tapme.customers.transfer_api import ExportView, ImportView
from tapme.feedback.api import FeedbackView, ResolveView
from tapme.media.api import PhotoFileView, PhotoListView
from tapme.messaging.api import (
    ChannelActionView,
    ChannelView,
    ChannelWebhookView,
    ChatAttachmentView,
    ChatDetailView,
    ChatFileView,
    ChatFolderDetailView,
    ChatFolderListView,
    ChatFoldersView,
    ChatListView,
    ChatMessagesView,
    ChatPaymentView,
    ChatReadView,
    ChatRetryView,
    ChatSummaryView,
    PaymentSettingsView,
    QuickReplyDetailView,
    QuickReplyView,
    whatsapp_webhook,
)
from tapme.orders.api import OrderDetailView, OrderListView
from tapme.orders.desk_api import DeskView, NoteDoneView, NotesView
from tapme.orders.draft_api import (
    DraftConvertView,
    DraftExtractView,
    DraftRestoreView,
    DraftView,
    ExtendPaymentView,
)
from tapme.orders.overview_api import OverviewView
from tapme.orders.public_api import PublicView, ShareView
from tapme.orders.workflow_api import (
    AssignmentView,
    DeliveryIssueView,
    EditView,
    HistoryView,
    PaymentListView,
    ResolveDeliveryIssueView,
    TaskListView,
    TransitionView,
)
from tapme.reminders.api import (
    ConfigurationView,
    ReminderActionView,
    ReminderListView,
    ReminderMessageView,
    ReminderOpenView,
    RulesView,
)

urlpatterns = [
    path(
        "api/v1/businesses/<uuid:business_id>/chats/<uuid:chat_id>/order-draft/extract/",
        DraftExtractView.as_view(),
    ),
    path(
        "api/v1/businesses/<uuid:business_id>/chats/<uuid:chat_id>/order-draft/",
        DraftView.as_view(),
    ),
    path(
        "api/v1/businesses/<uuid:business_id>/chats/<uuid:chat_id>/order-draft/convert/",
        DraftConvertView.as_view(),
    ),
    path(
        "api/v1/businesses/<uuid:business_id>/chats/<uuid:chat_id>/order-draft/restore/",
        DraftRestoreView.as_view(),
    ),
    path(
        "api/v1/businesses/<uuid:business_id>/orders/<uuid:order_id>/extend-payment/",
        ExtendPaymentView.as_view(),
    ),
    path(
        "api/v1/businesses/<uuid:business_id>/chats/<uuid:chat_id>/attachments/",
        ChatAttachmentView.as_view(),
    ),
    path(
        "api/v1/businesses/<uuid:business_id>/chats/<uuid:chat_id>/messages/<int:message_id>/file/",
        ChatFileView.as_view(),
    ),
    path("api/v1/webhooks/meta/whatsapp/", whatsapp_webhook),
    path("api/v1/webhooks/meta/whatsapp/<str:webhook_key>/", ChannelWebhookView.as_view()),
    path(
        "api/v1/businesses/<uuid:business_id>/channels/whatsapp/<str:action>/",
        ChannelActionView.as_view(),
    ),
    path(
        "api/v1/businesses/<uuid:business_id>/channels/payment-qr/", PaymentSettingsView.as_view()
    ),
    path("api/v1/businesses/<uuid:business_id>/quick-replies/", QuickReplyView.as_view()),
    path(
        "api/v1/businesses/<uuid:business_id>/quick-replies/<uuid:reply_id>/",
        QuickReplyDetailView.as_view(),
    ),
    path("api/v1/businesses/<uuid:business_id>/chats/summary/", ChatSummaryView.as_view()),
    path(
        "api/v1/businesses/<uuid:business_id>/chats/<uuid:chat_id>/payment-qr/",
        ChatPaymentView.as_view(),
    ),
    path("api/v1/businesses/<uuid:business_id>/channels/whatsapp/", ChannelView.as_view()),
    path("api/v1/businesses/<uuid:business_id>/chats/", ChatListView.as_view()),
    path("api/v1/businesses/<uuid:business_id>/chat-folders/", ChatFolderListView.as_view()),
    path(
        "api/v1/businesses/<uuid:business_id>/chat-folders/<uuid:folder_id>/",
        ChatFolderDetailView.as_view(),
    ),
    path(
        "api/v1/businesses/<uuid:business_id>/chats/<uuid:chat_id>/folders/",
        ChatFoldersView.as_view(),
    ),
    path("api/v1/businesses/<uuid:business_id>/chats/<uuid:chat_id>/", ChatDetailView.as_view()),
    path(
        "api/v1/businesses/<uuid:business_id>/chats/<uuid:chat_id>/messages/",
        ChatMessagesView.as_view(),
    ),
    path("api/v1/businesses/<uuid:business_id>/chats/<uuid:chat_id>/read/", ChatReadView.as_view()),
    path(
        "api/v1/businesses/<uuid:business_id>/chats/<uuid:chat_id>/messages/<int:message_id>/retry/",
        ChatRetryView.as_view(),
    ),
    path("api/v1/businesses/<uuid:business_id>/orders/desk/", DeskView.as_view()),
    path("api/v1/businesses/<uuid:business_id>/office-tasks/", NotesView.as_view()),
    path(
        "api/v1/businesses/<uuid:business_id>/office-tasks/<uuid:note_id>/done/",
        NoteDoneView.as_view(),
    ),
    path("health/", health),
    path("admin/", admin.site.urls),
    path("api/v1/auth/csrf/", CsrfView.as_view()),
    path("api/v1/auth/login/", LoginView.as_view()),
    path("api/v1/auth/logout/", LogoutView.as_view()),
    path("api/v1/auth/me/", MeView.as_view()),
    path("api/v1/businesses/", BusinessListView.as_view()),
    path("api/v1/businesses/<uuid:business_id>/customers/directory/", DirectoryView.as_view()),
    path("api/v1/businesses/<uuid:business_id>/customers/", CustomerListView.as_view()),
    path("api/v1/businesses/<uuid:business_id>/products/", ProductListView.as_view()),
    path(
        "api/v1/businesses/<uuid:business_id>/products/<uuid:product_id>/photo/",
        ProductPhotoView.as_view(),
    ),
    path("api/v1/businesses/<uuid:business_id>/orders/", OrderListView.as_view()),
    path("api/v1/businesses/<uuid:business_id>/orders/<uuid:order_id>/", OrderDetailView.as_view()),
    path(
        "api/schema/",
        SpectacularAPIView.as_view(permission_classes=[IsAuthenticated]),
        name="schema",
    ),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema", permission_classes=[IsAuthenticated]),
    ),
]

urlpatterns += [path("api/v1/businesses/<uuid:business_id>/tasks/", TaskListView.as_view())]
for route, view in [
    ("edit", EditView),
    ("assignment", AssignmentView),
    ("transition", TransitionView),
    ("delivery-issue", DeliveryIssueView),
    ("payments", PaymentListView),
    ("history", HistoryView),
]:
    urlpatterns.append(
        path(
            f"api/v1/businesses/<uuid:business_id>/orders/<uuid:order_id>/{route}/", view.as_view()
        )
    )


urlpatterns += [
    path(
        "api/v1/businesses/<uuid:business_id>/orders/<uuid:order_id>/photos/",
        PhotoListView.as_view(),
    ),
    path(
        "api/v1/businesses/<uuid:business_id>/orders/<uuid:order_id>/photos/<uuid:photo_id>/",
        PhotoFileView.as_view(),
    ),
]


urlpatterns += [
    path("api/v1/businesses/<uuid:business_id>/settings/", SettingsView.as_view()),
    path("api/v1/businesses/<uuid:business_id>/staff/", StaffView.as_view()),
    path("api/v1/businesses/<uuid:business_id>/staff/<uuid:user_id>/", StaffDetailView.as_view()),
]


urlpatterns += [
    path(
        "api/v1/businesses/<uuid:business_id>/customers/<uuid:customer_id>/",
        CustomerDetailView.as_view(),
    )
]


urlpatterns += [
    path(
        "api/v1/businesses/<uuid:business_id>/orders/<uuid:order_id>/feedback/",
        FeedbackView.as_view(),
    ),
    path(
        "api/v1/businesses/<uuid:business_id>/feedback/<uuid:feedback_id>/resolve/",
        ResolveView.as_view(),
    ),
]


urlpatterns += [
    path("api/v1/businesses/<uuid:business_id>/reminders/", ReminderListView.as_view()),
    path("api/v1/businesses/<uuid:business_id>/reminder-rules/", RulesView.as_view()),
    path("api/v1/businesses/<uuid:business_id>/reminder-scenarios/", ConfigurationView.as_view()),
    path(
        "api/v1/businesses/<uuid:business_id>/reminders/<uuid:reminder_id>/open/",
        ReminderOpenView.as_view(),
    ),
    path(
        "api/v1/businesses/<uuid:business_id>/reminders/<uuid:reminder_id>/message/",
        ReminderMessageView.as_view(),
    ),
    path(
        "api/v1/businesses/<uuid:business_id>/reminders/<uuid:reminder_id>/action/",
        ReminderActionView.as_view(),
    ),
]


urlpatterns += [
    path("api/v1/businesses/<uuid:business_id>/customers/import/", ImportView.as_view()),
    path("api/v1/businesses/<uuid:business_id>/customers/export/", ExportView.as_view()),
]


urlpatterns += [
    path("api/v1/public/orders/<str:token>/", PublicView.as_view()),
    path("api/v1/businesses/<uuid:business_id>/orders/<uuid:order_id>/share/", ShareView.as_view()),
    path("api/v1/businesses/<uuid:business_id>/overview/", OverviewView.as_view()),
]


urlpatterns += [
    path("api/v1/auth/password/", PasswordView.as_view()),
    path(
        "api/v1/businesses/<uuid:business_id>/staff/<uuid:user_id>/reset-password/",
        ResetStaffView.as_view(),
    ),
]


urlpatterns += [
    path(
        "api/v1/businesses/<uuid:business_id>/products/<uuid:product_id>/",
        ProductDetailView.as_view(),
    )
]


urlpatterns += [
    path(
        "api/v1/businesses/<uuid:business_id>/orders/<uuid:order_id>/resolve-delivery-issue/",
        ResolveDeliveryIssueView.as_view(),
    )
]


urlpatterns += [
    path(
        "api/v1/businesses/<uuid:business_id>/customers/<uuid:customer_id>/activity/",
        ActivityView.as_view(),
    )
]


urlpatterns += [
    path("api/v1/businesses/<uuid:business_id>/points/", PointsView.as_view()),
    path("api/v1/businesses/<uuid:business_id>/points/<uuid:point_id>/", PointDetailView.as_view()),
    path(
        "api/v1/businesses/<uuid:business_id>/points/<uuid:point_id>/archive/",
        PointArchiveView.as_view(),
    ),
    path(
        "api/v1/businesses/<uuid:business_id>/staff/<uuid:user_id>/points/",
        StaffPointsView.as_view(),
    ),
]
