from django.urls import path
from dashboard import views

urlpatterns = [
    path("", views.command_center, name="command_center"),
    path("toggle/", views.toggle_switch, name="toggle_switch"),
    path("jobs/", views.jobs, name="jobs"),
    path("activity/", views.activity_page, name="activity"),
    path("skills/", views.skill_gap_page, name="skills"),
    path("tracker/", views.tracker, name="tracker"),
    path("tracker/update/", views.update_application, name="update_application"),
    path("outreach/", views.outreach_book, name="outreach"),
    path("resume/", views.resume_studio, name="resume"),
    path("resume/decide/", views.decide_edit, name="decide_edit"),
    path("my-resume/", views.my_resume, name="my_resume"),
    path("mark-applied/", views.mark_applied, name="mark_applied"),
    path("interview/", views.interview_prep_page, name="interview"),
    path("grow/", views.grow_page, name="grow"),
    path("mock/", views.mock_interview_page, name="mock"),
    path("mock/feedback/", views.mock_feedback, name="mock_feedback"),
    path("chat/", views.chat_page, name="chat"),
    path("chat/send/", views.chat_send, name="chat_send"),
    path("live/", views.live_page, name="live"),
]
