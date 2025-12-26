from django.contrib import admin
from .models.Achievement import Achievement
from .models.Boss import Boss
from .models.BusinessUser import BusinessUser
from .models.BossAttack import BossAttack
from .models.Project import Project
from .models.ProjectBoss import ProjectBoss
from .models.ProjectMember import ProjectMember
from .models.Report import Report
from .models.Task import Task
from .models.TaskLog import TaskLog
from .models.UserAchievement import UserAchievement
from .models.UserAttack import UserAttack
from .models.UserBossCollection import UserBossCollection
from .models.UserFeedback import UserFeedback
from .models.UserReport import UserReport
from .models.UserTask import UserTask

admin.site.register(Achievement)
admin.site.register(Boss)
admin.site.register(BossAttack)
admin.site.register(Project)
admin.site.register(ProjectBoss)
admin.site.register(ProjectMember)
admin.site.register(Report)
admin.site.register(Task)
admin.site.register(TaskLog)
admin.site.register(BusinessUser)
admin.site.register(UserAchievement)
admin.site.register(UserAttack)
admin.site.register(UserBossCollection)
admin.site.register(UserFeedback)
admin.site.register(UserReport)
admin.site.register(UserTask)



