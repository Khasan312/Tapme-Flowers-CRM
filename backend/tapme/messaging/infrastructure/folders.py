from django.db import transaction
from django.db.models import Count, Q

from tapme.businesses.models import Business
from tapme.messaging.models import ChatFolder, Conversation
from tapme.shared.domain import Conflict, InvalidInput, NotFound


class ChatFolders:
    def _folder(self, scope, folder_id, lock=False):
        qs = ChatFolder.objects.filter(business_id=scope.business_id)
        if lock:
            qs = qs.select_for_update()
        folder = qs.filter(id=folder_id).first()
        if not folder:
            raise NotFound("Папка не найдена.")
        return folder

    def folders(self, scope, channel_kind="whatsapp"):
        folders = (
            ChatFolder.objects.filter(business_id=scope.business_id)
            .annotate(
                count=Count(
                    "conversations",
                    filter=~Q(conversations__mode="closed")
                    & Q(conversations__channel__kind=channel_kind),
                ),
                total=Count("conversations", filter=Q(conversations__channel__kind=channel_kind)),
            )
            .order_by("created_at", "id")
        )
        return {
            "results": [
                {
                    "id": str(f.id),
                    "name": f.name,
                    "version": f.version,
                    "count": f.count,
                    "total": f.total,
                }
                for f in folders
            ],
            "all_count": Conversation.objects.filter(
                channel__business_id=scope.business_id, channel__kind=channel_kind
            )
            .exclude(mode="closed")
            .count(),
        }

    def create_folder(self, scope, name):
        with transaction.atomic():
            # Serialize quota and normalized-name validation within the business.
            Business.objects.select_for_update().get(id=scope.business_id)
            if ChatFolder.objects.filter(business_id=scope.business_id).count() >= 30:
                raise InvalidInput("Можно создать до 30 папок.")
            name = self._folder_name(scope, name)
            folder = ChatFolder.objects.create(
                business_id=scope.business_id, name=name, name_key=name.casefold()
            )
        return {
            "id": str(folder.id),
            "name": folder.name,
            "version": folder.version,
            "count": 0,
            "total": 0,
        }

    def _folder_name(self, scope, name, folder_id=None):
        name = " ".join(name.split())
        if not name or len(name) > 40:
            raise InvalidInput("Укажите название папки от 1 до 40 символов.")
        existing = ChatFolder.objects.filter(
            business_id=scope.business_id, name_key=name.casefold()
        )
        if folder_id:
            existing = existing.exclude(id=folder_id)
        if existing.exists():
            raise InvalidInput("Папка с таким названием уже существует.")
        return name

    def rename_folder(self, scope, folder_id, name, version):
        with transaction.atomic():
            Business.objects.select_for_update().get(id=scope.business_id)
            folder = self._folder(scope, folder_id, lock=True)
            if folder.version != version:
                raise Conflict("Папка изменилась. Обновите список и повторите.")
            folder.name = self._folder_name(scope, name, folder.id)
            folder.name_key = folder.name.casefold()
            folder.version += 1
            folder.save(update_fields=["name", "name_key", "version"])
        return {"ok": True}

    def delete_folder(self, scope, folder_id, version):
        with transaction.atomic():
            folder = self._folder(scope, folder_id, lock=True)
            if folder.version != version:
                raise Conflict("Папка изменилась. Обновите список и повторите.")
            # Only the folder and its M2M links cascade; conversations stay intact.
            folder.delete()
        return {"ok": True}

    def set_chat_folders(self, scope, chat_id, folder_ids, version):
        with transaction.atomic():
            chat = self._conversation(scope, chat_id, lock=True)
            if chat.version != version:
                raise Conflict("Диалог изменился. Откройте выбор папок заново.")
            folders = list(
                ChatFolder.objects.select_for_update()
                .filter(business_id=scope.business_id, id__in=folder_ids)
                .order_by("id")
            )
            if len(folders) != len(set(folder_ids)):
                raise InvalidInput("Одна из папок больше не доступна. Обновите список.")
            chat.folders.set(folders)
            chat.version += 1
            chat.save(update_fields=["version"])
        return self.detail(scope, chat_id)
