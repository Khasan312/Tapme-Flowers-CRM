from datetime import UTC, datetime

from tapme.businesses.infrastructure.access import DjangoMembershipReader
from tapme.catalog.application.services import CatalogService
from tapme.catalog.infrastructure.repository import DjangoProductRepository
from tapme.customers.application.services import CustomerService
from tapme.customers.infrastructure.repository import DjangoCustomerRepository
from tapme.orders.application.services import OrderService
from tapme.orders.infrastructure.repository import DjangoOrderRepository, DjangoUnitOfWork


def customers():
    return CustomerService(DjangoMembershipReader(), DjangoCustomerRepository())


def catalog():
    return CatalogService(DjangoMembershipReader(), DjangoProductRepository())


def orders():
    return OrderService(
        DjangoMembershipReader(),
        DjangoCustomerRepository(),
        DjangoProductRepository(),
        DjangoUnitOfWork,
        DjangoOrderRepository(),
        lambda: datetime.now(UTC),
    )


def workflow():
    from tapme.orders.application.workflow import WorkflowService

    return WorkflowService(
        DjangoMembershipReader(),
        DjangoCustomerRepository(),
        DjangoProductRepository(),
        DjangoUnitOfWork,
        DjangoOrderRepository(),
        lambda: datetime.now(UTC),
    )


def photos():
    from tapme.media.application.services import PhotoService
    from tapme.media.infrastructure.storage import DjangoPhotoStorage

    return PhotoService(
        DjangoMembershipReader(), DjangoUnitOfWork, DjangoPhotoStorage(), lambda: datetime.now(UTC)
    )


def settings():
    from tapme.businesses.application.settings import BusinessSettingsService
    from tapme.businesses.infrastructure.settings import DjangoBusinessSettingsRepository

    return BusinessSettingsService(DjangoMembershipReader(), DjangoBusinessSettingsRepository())


def profiles():
    from tapme.customers.application.profile import ProfileService
    from tapme.customers.infrastructure.profile import DjangoProfileRepository

    return ProfileService(DjangoMembershipReader(), DjangoProfileRepository())


def feedback():
    from tapme.feedback.application.services import FeedbackService
    from tapme.feedback.infrastructure.repository import DjangoFeedbackRepository

    return FeedbackService(DjangoMembershipReader(), DjangoFeedbackRepository())


def reminders():
    from tapme.reminders.application.services import ReminderService
    from tapme.reminders.infrastructure.repository import DjangoReminderRepository

    return ReminderService(DjangoMembershipReader(), DjangoReminderRepository())


def reminder_generation():
    from tapme.businesses.infrastructure.access import business_ids
    from tapme.reminders.application.services import ReminderGeneration
    from tapme.reminders.infrastructure.repository import DjangoReminderRepository

    return ReminderGeneration(business_ids, DjangoReminderRepository())


def transfers():
    from tapme.customers.application.transfers import CustomerTransferService

    return CustomerTransferService(DjangoMembershipReader(), DjangoCustomerRepository())


def public_orders():
    from tapme.orders.application.public import PublicOrderService
    from tapme.orders.infrastructure.public import DjangoPublicOrderRepository

    return PublicOrderService(DjangoMembershipReader(), DjangoPublicOrderRepository())


def overview():
    from tapme.orders.application.overview import OverviewService
    from tapme.orders.infrastructure.overview import DjangoOverviewReader

    return OverviewService(DjangoMembershipReader(), DjangoOverviewReader())


def customer_activity():
    from tapme.customers.application.activity import ActivityService
    from tapme.customers.infrastructure.activity import DjangoActivityReader

    return ActivityService(DjangoMembershipReader(), DjangoActivityReader())


def order_desk():
    from tapme.orders.application.desk import OrderDeskService
    from tapme.orders.infrastructure.desk import DjangoOrderDesk

    return OrderDeskService(DjangoMembershipReader(), DjangoOrderDesk())


def customer_directory():
    from tapme.customers.application.directory import DirectoryService
    from tapme.customers.infrastructure.directory import DjangoDirectoryReader

    return DirectoryService(DjangoMembershipReader(), DjangoDirectoryReader())
