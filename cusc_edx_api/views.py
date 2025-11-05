# cusc_edx_api/views.py
import json

from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from opaque_keys import InvalidKeyError
from common.djangoapps.course_modes.models import CourseMode

from opaque_keys.edx.keys import CourseKey
from common.djangoapps.student.models import CourseEnrollment

from .models import EcommerceOrder

User = get_user_model()


def ping(request):
    return JsonResponse({"ok": True, "app": "cusc_edx_api"})


# ==== (optional) bảo vệ endpoint bằng header secret đơn giản ==== #
PAYMENT_API_TOKEN = getattr(settings, "CUSC_PAYMENT_API_TOKEN", None)


def _check_node_auth(request):
    """
    Kiểu bảo vệ tối thiểu:
    - Đặt CUSC_PAYMENT_API_TOKEN trong settings
    - Node.js gửi header: X-CUSC-PAYMENT-TOKEN: <token>
    Nếu chưa set token thì coi như tắt auth (DEV).
    """
    if not PAYMENT_API_TOKEN:
        return None  # auth off (dev)
    token = request.headers.get("X-CUSC-PAYMENT-TOKEN")
    if token != PAYMENT_API_TOKEN:
        return JsonResponse({"error": "Unauthorized"}, status=401)
    return None


def _parse_json(request):
    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        return None, JsonResponse({"error": "Invalid JSON body"}, status=400)
    return data, None


def _get_user_from_payload(data):
    user_id = data.get("user_id")
    username = data.get("username")
    email = data.get("email")

    if not (user_id or username or email):
        return None, JsonResponse(
            {"error": "Missing user identifier (user_id | username | email)"},
            status=400,
        )

    try:
        if user_id:
            user = User.objects.get(id=user_id)
        elif username:
            user = User.objects.get(username=username)
        else:
            user = User.objects.get(email=email)
        return user, None
    except User.DoesNotExist:
        return None, JsonResponse({"error": "User not found"}, status=404)


# ========= 1) Tạo order từ Node.js ========= #

@csrf_exempt
def create_order(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    # auth đơn giản
    auth_resp = _check_node_auth(request)
    if auth_resp is not None:
        return auth_resp

    data, err = _parse_json(request)
    if err:
        return err

    # required fields
    course_id = data.get("course_id")
    raw_amount = data.get("amount")
    currency = data.get("currency") or "VND"
    external_order_id = data.get("external_order_id")
    extra_data = data.get("extra_data") or {}

    if not course_id:
        return JsonResponse({"error": "Missing course_id"}, status=400)

    amount = EcommerceOrder.parse_amount(raw_amount)
    if amount is None:
        return JsonResponse({"error": "Missing or invalid amount"}, status=400)

    user, err = _get_user_from_payload(data)
    if err:
        return err

    order = EcommerceOrder.objects.create(
        user=user,
        course_id=course_id,
        amount=amount,
        currency=currency,
        external_order_id=external_order_id,
        extra_data=extra_data,
    )

    return JsonResponse(order.to_dict(), status=201)


# ========= 2) Xem chi tiết order ========= #

@require_GET
def order_detail(request, order_id):
    order = get_object_or_404(EcommerceOrder, id=order_id)
    return JsonResponse(order.to_dict())


# ========= 3) List order (filter cơ bản) ========= #

@require_GET
def order_list(request):
    qs = EcommerceOrder.objects.all()

    status_param = request.GET.get("status")
    user_id = request.GET.get("user_id")
    username = request.GET.get("username")
    external_order_id = request.GET.get("external_order_id")

    if status_param:
        qs = qs.filter(status=status_param)
    if user_id:
        qs = qs.filter(user_id=user_id)
    if username:
        qs = qs.filter(user__username=username)
    if external_order_id:
        qs = qs.filter(external_order_id=external_order_id)

    qs = qs[:50]  # limit cho nhẹ

    return JsonResponse(
        {
            "count": qs.count(),
            "results": [o.to_dict() for o in qs],
        }
    )


# ========= 4) Node.js báo trạng thái thanh toán ========= #

@csrf_exempt
@require_POST
def update_order_status(request, order_id):
    # auth đơn giản
    auth_resp = _check_node_auth(request)
    if auth_resp is not None:
        return auth_resp

    data, err = _parse_json(request)
    if err:
        return err

    new_status = data.get("status")
    if new_status not in dict(EcommerceOrder.STATUS_CHOICES):
        return JsonResponse(
            {
                "error": "Invalid status",
                "allowed": list(dict(EcommerceOrder.STATUS_CHOICES).keys()),
            },
            status=400,
        )

    order = get_object_or_404(EcommerceOrder, id=order_id)

    # idempotent: nếu đã ở trạng thái đó thì trả luôn
    if order.status == new_status:
        return JsonResponse(order.to_dict())

    order.status = new_status
    # lưu thêm thông tin giao dịch nếu muốn
    extra_data = order.extra_data or {}
    if "payment_info" in data:
        extra_data["payment_info"] = data["payment_info"]
    order.extra_data = extra_data
    order.save()

    enrollment_created = False

    # Nếu đã thanh toán thành công => enroll vào course
    if new_status == EcommerceOrder.STATUS_PAID:
        try:
            course_key = CourseKey.from_string(order.course_id)
        except Exception:
            return JsonResponse(
                {
                    "error": "Invalid course_id format",
                    "order": order.to_dict(),
                },
                status=400,
            )

        # tránh tạo trùng
        if not CourseEnrollment.objects.filter(
            user=order.user,
            course_id=course_key,
            is_active=True,
        ).exists():
            CourseEnrollment.enroll(order.user, course_key, mode="verified")
            enrollment_created = True

    resp = order.to_dict()
    resp["enrollment_created"] = enrollment_created
    return JsonResponse(resp)


@csrf_exempt
@require_GET
def user_lookup(request):
    """
    GET /api/cusc-edx-api/users/lookup/?username=...&email=...

    Trả về danh sách user khớp (thường là 0 hoặc 1).
    """
    # 1) check token giống các API ecommerce khác
    auth_error = _check_node_auth(request)  # hoặc _check_node_auth(...) nếu bạn đặt tên vậy
    if auth_error is not None:
        return auth_error

    username = request.GET.get("username")
    email = request.GET.get("email")

    if not username and not email:
        return JsonResponse(
            {"error": "Phải truyền ít nhất username hoặc email"},
            status=400,
        )

    qs = User.objects.all()

    if username:
        qs = qs.filter(username=username)

    if email:
        # so khớp không phân biệt hoa thường cho email
        qs = qs.filter(email__iexact=email)

    users = [
        {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "is_active": u.is_active,
        }
        for u in qs
    ]

    return JsonResponse(
        {
            "count": len(users),
            "results": users,
        }
    )
    
@require_GET
def course_pricing(request, course_id):
    """
    GET /api/cusc-edx-api/course-pricing/?course_id=...&mode=verified

    - Bắt buộc: course_id (vd: course-v1:ORG+CODE+RUN)
    - Optional: mode (vd: verified, audit,...)
      Nếu không truyền mode => trả về tất cả course modes của course đó.
    """
    # bảo vệ bằng token giống các API khác
    auth_error = _check_node_auth(request)
    if auth_error is not None:
        return auth_error

    course_id_str = course_id
    if not course_id_str:
        return JsonResponse(
            {"error": "Missing course_id"},
            status=400,
        )

    mode_slug = request.GET.get("mode")  # ví dụ: verified

    # parse course_id -> CourseKey
    try:
        course_key = CourseKey.from_string(course_id_str)
    except InvalidKeyError:
        return JsonResponse(
            {"error": f"Invalid course_id '{course_id_str}'"},
            status=400,
        )

    qs = CourseMode.objects.filter(course_id=course_key)

    if mode_slug:
        qs = qs.filter(mode_slug=mode_slug)

    if not qs.exists():
        return JsonResponse(
            {"error": "Không tìm thấy pricing cho course này"},
            status=404,
        )

    modes_data = []
    for m in qs:
        modes_data.append(
            {
                "mode_slug": getattr(m, "mode_slug", None),
                "mode_display_name": getattr(m, "mode_display_name", None),
                "currency": getattr(m, "currency", None),
                # Decimal -> string để JSON không lỗi
                "price": (
                    str(getattr(m, "min_price", None))
                    if getattr(m, "min_price", None) is not None
                    else None
                ),
                "sku": getattr(m, "sku", None),
                "bulk_sku": getattr(m, "bulk_sku", None),
                "expiration_datetime": (
                    m.expiration_datetime.isoformat()
                    if getattr(m, "expiration_datetime", None)
                    else None
                ),
                "expiration_date": (
                    m.expiration_date.isoformat()
                    if getattr(m, "expiration_date", None)
                    else None
                ),
                "is_active": getattr(m, "is_active", None),
            }
        )

    return JsonResponse(
        {
            "course_id": course_id_str,
            "modes": modes_data,
        }
    )