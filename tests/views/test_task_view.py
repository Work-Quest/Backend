from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory

from tests.drf_helpers import attach_authenticated_user

from api.views import task_view as tv


class TaskViewTest(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    @patch("api.views.task_view.TaskResponseSerializer")
    @patch("api.views.task_view.TaskService")
    @patch("api.views.task_view.CacheService")
    @patch("api.views.task_view.BusinessUser.objects.get")
    def test_task_list(self, mock_bu, mock_cache_cls, mock_ts, mock_ser_cls):
        mock_bu.return_value = MagicMock(user_id="u1")
        inst = MagicMock()
        inst.data = []
        mock_ser_cls.return_value = inst
        mock_ts.return_value.get_all_tasks.return_value = []
        cache = MagicMock()
        cache.keys.project_tasks.return_value = "k"
        cache.read_through.side_effect = lambda **kw: kw["loader"]()
        mock_cache_cls.return_value = cache
        request = self.factory.get("/tasks/")
        attach_authenticated_user(request)
        response = tv.task_list(request, project_id="00000000-0000-0000-0000-000000000001")
        self.assertEqual(response.status_code, 200)

    @patch("api.views.task_view.CacheService")
    @patch("api.views.task_view.TaskResponseSerializer")
    @patch("api.views.task_view.TaskRequestSerializer")
    @patch("api.views.task_view.TaskService")
    @patch("api.views.task_view.BusinessUser.objects.get")
    def test_task_create_valid(self, mock_bu, mock_ts, mock_req, mock_resp, _cache):
        mock_bu.return_value = MagicMock()
        mock_req.return_value.is_valid.return_value = True
        mock_req.return_value.validated_data = {"task_name": "a"}
        mock_ts.return_value.create_task.return_value = MagicMock()
        mock_resp.return_value.data = {"task_id": "t1"}
        request = self.factory.post("/tasks/", {"task_name": "a"}, format="json")
        attach_authenticated_user(request)
        r = tv.task_create(request, project_id="00000000-0000-0000-0000-000000000001")
        self.assertEqual(r.status_code, 201)

    @patch("api.views.task_view.TaskRequestSerializer")
    @patch("api.views.task_view.TaskService")
    @patch("api.views.task_view.BusinessUser.objects.get")
    def test_task_create_invalid(self, mock_bu, mock_ts, mock_req):
        mock_bu.return_value = MagicMock()
        mock_req.return_value.is_valid.return_value = False
        mock_req.return_value.errors = {"e": 1}
        request = self.factory.post("/tasks/", {}, format="json")
        attach_authenticated_user(request)
        r = tv.task_create(request, project_id="00000000-0000-0000-0000-000000000001")
        self.assertEqual(r.status_code, 400)

    @patch("api.views.task_view.TaskResponseSerializer")
    @patch("api.views.task_view.TaskService")
    @patch("api.views.task_view.CacheService")
    @patch("api.views.task_view.BusinessUser.objects.get")
    def test_task_detail_found(self, mock_bu, mock_cache_cls, mock_ts, mock_ser):
        mock_bu.return_value = MagicMock(user_id="u1")
        mock_ts.return_value.get_task.return_value = MagicMock()
        mock_ser.return_value.data = {"task_id": "x"}
        cache = MagicMock()
        cache.keys.task_detail.return_value = "k"
        cache.read_through.side_effect = lambda **kw: kw["loader"]()
        mock_cache_cls.return_value = cache
        request = self.factory.get("/tasks/t/")
        attach_authenticated_user(request)
        r = tv.task_detail(request, "00000000-0000-0000-0000-000000000001", "t1")
        self.assertEqual(r.status_code, 200)

    @patch("api.views.task_view.TaskService")
    @patch("api.views.task_view.CacheService")
    @patch("api.views.task_view.BusinessUser.objects.get")
    def test_task_detail_not_found(self, mock_bu, mock_cache_cls, mock_ts):
        mock_bu.return_value = MagicMock(user_id="u1")
        mock_ts.return_value.get_task.return_value = None
        cache = MagicMock()
        cache.keys.task_detail.return_value = "k"
        cache.read_through.side_effect = lambda **kw: kw["loader"]()
        mock_cache_cls.return_value = cache
        request = self.factory.get("/tasks/t/")
        attach_authenticated_user(request)
        r = tv.task_detail(request, "00000000-0000-0000-0000-000000000001", "t1")
        self.assertEqual(r.status_code, 404)

    @patch("api.views.task_view.TaskResponseSerializer")
    @patch("api.views.task_view.CacheService")
    @patch("api.views.task_view.TaskService")
    @patch("api.views.task_view.BusinessUser.objects.get")
    def test_task_move(self, mock_bu, mock_ts, _c, mock_ser):
        mock_bu.return_value = MagicMock()
        mock_ts.return_value.get_task.return_value = MagicMock()
        moved = MagicMock()
        mock_ts.return_value.move_task.return_value = moved
        mock_ser.return_value.data = {"task_id": "t1"}
        request = self.factory.patch("/tasks/t/", {"status": "done"}, format="json")
        attach_authenticated_user(request)
        r = tv.task_move(request, "00000000-0000-0000-0000-000000000001", "t1")
        self.assertEqual(r.status_code, 200)

    @patch("api.views.task_view.TaskResponseSerializer")
    @patch("api.views.task_view.TaskRequestSerializer")
    @patch("api.views.task_view.CacheService")
    @patch("api.views.task_view.TaskService")
    @patch("api.views.task_view.BusinessUser.objects.get")
    def test_task_update(self, mock_bu, mock_ts, _c, mock_req, mock_resp):
        mock_bu.return_value = MagicMock()
        mock_ts.return_value.get_task.return_value = MagicMock()
        mock_req.return_value.is_valid.return_value = True
        mock_req.return_value.validated_data = {}
        updated = MagicMock()
        mock_ts.return_value.edit_task.return_value = updated
        mock_resp.return_value.data = {"task_id": "t1"}
        request = self.factory.put("/tasks/t/", {"task_name": "x"}, format="json")
        attach_authenticated_user(request)
        self.assertEqual(
            tv.task_update(request, "00000000-0000-0000-0000-000000000001", "t1").status_code,
            200,
        )

    @patch("api.views.task_view.CacheService")
    @patch("api.views.task_view.TaskService")
    @patch("api.views.task_view.BusinessUser.objects.get")
    def test_task_delete(self, mock_bu, mock_ts, _c):
        mock_bu.return_value = MagicMock()
        mock_ts.return_value.delete_task.return_value = True
        request = self.factory.delete("/tasks/t/")
        attach_authenticated_user(request)
        self.assertEqual(
            tv.task_delete(request, "00000000-0000-0000-0000-000000000001", "t1").status_code,
            204,
        )

    def test_task_assign_requires_project_member_id(self):
        request = self.factory.post("/tasks/", {}, format="json")
        attach_authenticated_user(request)
        response = tv.task_assign(request, project_id="p", task_id="t")
        self.assertEqual(response.status_code, 400)

    @patch("api.views.task_view.CacheService")
    @patch("api.views.task_view.TaskService")
    @patch("api.views.task_view.BusinessUser.objects.get")
    def test_task_assign_success(self, mock_bu, mock_ts, _c):
        mock_bu.return_value = MagicMock()
        mock_ts.return_value.assign_user_to_task.return_value = (MagicMock(), True)
        request = self.factory.post("/tasks/", {"project_member_id": "m1"}, format="json")
        attach_authenticated_user(request)
        self.assertEqual(tv.task_assign(request, "pid", "tid").status_code, 201)

    @patch("api.views.task_view.CacheService")
    @patch("api.views.task_view.TaskService")
    @patch("api.views.task_view.BusinessUser.objects.get")
    def test_task_unassign(self, mock_bu, mock_ts, _c):
        mock_bu.return_value = MagicMock()
        mock_ts.return_value.unassign_user_from_task.return_value = True
        request = self.factory.delete(
            "/tasks/",
            {"project_member_id": "m1"},
            format="json",
        )
        attach_authenticated_user(request)
        self.assertEqual(tv.task_unassign(request, "pid", "tid").status_code, 204)
