# cusc_edx_api/management/commands/cleanup_cusc_orders.py
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from cusc_edx_api.models import EcommerceOrder


class Command(BaseCommand):
    help = "Dọn các order PENDING đã quá hạn"

    def add_arguments(self, parser):
        parser.add_argument(
            "--ttl-seconds",
            type=int,
            default=60,  # 24h = 86400 giây
            help="Order pending lâu hơn số GIÂY này sẽ bị xử lý.",
        )
        parser.add_argument(
            "--delete",
            action="store_true",
            help="Nếu truyền flag này thì xóa hẳn record. "
                 "Nếu KHÔNG truyền thì chỉ chuyển sang status=expired.",
        )
        
        parser.add_argument(
            "--delete-after-days",
            type=int,
            default=None,
            help=(
                "Khi dùng kèm với --delete: chỉ xóa order đã tạo lâu hơn N ngày. "
                "Nếu không truyền, sẽ xóa theo ttl-seconds."
            ),
        )

    def handle(self, *args, **options):
        ttl_seconds = options["ttl_seconds"]
        delete_records = options["delete"]
        delete_after_days = options.get("delete_after_days")

        now = timezone.now()
        cutoff = now - timedelta(seconds=ttl_seconds)

        qs = EcommerceOrder.objects.filter(
            status=EcommerceOrder.STATUS_PENDING,
            created_at__lt=cutoff,
        )

        count = qs.count()

        if not count:
            self.stdout.write("Không có order pending quá hạn.")
            return

        if delete_records:
            delete_qs = qs
            msg_suffix = f"cũ hơn {ttl_seconds} giây."

            # 👇 Nếu có truyền --delete-after-days thì lọc thêm theo ngày
            if delete_after_days is not None:
                delete_cutoff = now - timedelta(days=delete_after_days)
                delete_qs = delete_qs.filter(created_at__lt=delete_cutoff)
                msg_suffix = f"cũ hơn {delete_after_days} ngày."

            deleted_count, _ = delete_qs.delete()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Đã XÓA {deleted_count} order pending {msg_suffix}"
                )
            )
        else:
            updated = qs.update(
                status=EcommerceOrder.STATUS_EXPIRED,
                expired_at=now,
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Đã đánh dấu EXPIRED {updated} order pending cũ hơn {ttl_seconds} giây."
                )
            )
