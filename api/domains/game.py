from Backend.api.models import UserEffect
from api.models import UserItem
from api.models import Item
from api.models.ProjectBoss import ProjectBoss
from api.domains.boss import Boss as BossDomain
from api.models.Boss import Boss
import datetime
import django.urls
import random
from django.utils import timezone
from api.models import TaskLog
from api.domains.review import Review
from django.utils import timezone
from api.dtos.review_dto import TaskFacts
from api.models import UserReport


class Game:
    def __init__(self, project_domain):
        self._project = project_domain
        self._task_management = project_domain.TaskManagement
        self._project_member_management = project_domain.project_member_management
        self._review = Review()
        self._players = self._project_member_management.members

        self._boss = None

        self.BASE_BOSS_HP = 1000
        self.BASE_PLAYER_DAMAGE = 1000
        self.BASE_BOSS_DAMAGE = 10

        self.BASE_SCORE = 0.1
        self.BASE_SPECIAL_BOSS_HP = 5000

    @property
    def players(self):
        return self._players
    
    @property
    def boss(self):
        if self._boss is not None:
            return self._boss

        project_boss = (
            ProjectBoss.objects
            .filter(project=self._project.project)
            .order_by("-created_at")
            .first()
        )

        if project_boss is None:
            return None
        self._boss = BossDomain(project_boss)
        return self._boss

    def initail_boss_set_up(self):
        existing = self.boss
        if existing is not None and existing.boss is not None:
            raise ValueError("Boss already initialized")
        
        project_boss_model = ProjectBoss.objects.create(project=self._project.project, boss=None, hp=0, max_hp=0, status="Alive")
        self._boss = BossDomain(project_boss_model)

        # Boss.boss_type choices are "Normal" / "Special" (see api.models.Boss)
        all_boss = list(Boss.objects.filter(boss_type="Normal"))
        if not all_boss:
            raise ValueError('No "Normal" bosses configured in the database')
        selected_boss = random.choice(all_boss)
        self._boss.boss = selected_boss

        all_tasks = self._task_management.tasks
        if not all_tasks:
            raise ValueError("Cannot setup boss: project has no tasks")
        total_priority = sum(task.priority for task in all_tasks)
        if total_priority <= 0:
            raise ValueError("Cannot setup boss: total task priority must be greater than 0")
        boss_hp = total_priority * self.BASE_BOSS_HP
        self._boss.max_hp = boss_hp
        self._boss.full_heal()
        self._boss.updated_at = timezone.now()
        return self._boss

    def next_phase_boss_setup(self):
        add_log = TaskLog.objects.filter(
            project_member__project=self._project.project,
            action_type="USER",
            event="TASK_CREATED",
            created_at__gt=self._boss.updated_at
        )

        delete_log = TaskLog.objects.filter(
            project_member__project=self._project.project,
            action_type="USER",
            event="TASK_DELETED",
            created_at__gt=self._boss.updated_at
        )
        
        print("add_log:", add_log)

        if not add_log:
            return None

        add_value = sum(log.task.priority for log in add_log)
        delete_value = sum(log.task_priority_snapshot for log in delete_log)
        print(add_value)
        print(delete_value)
        net_change = add_value - delete_value
        hp_change = net_change * self.BASE_BOSS_HP
        
        if hp_change <= 0:
            return None
        
        # set up boss next phase
        self.boss.max_hp = hp_change
        self.boss.hp = hp_change
        self.boss.phase += 1

        self.boss.updated_at = timezone.now()

        return  self.boss.project_boss
    

    def special_boss_setup(self):
        all_boss = Boss.objects.filter(boss_type="Special")
        # exclude existed boss in case already defeat specail boss once
        existed_boss_ids = ProjectBoss.objects.filter(
            project=self._project.project
        ).values_list("boss_id", flat=True)

        available_bosses = all_boss
        if existed_boss_ids:
            available_bosses = all_boss.exclude(
                    boss_id__in=existed_boss_ids
                )

        available_bosses_list = list(available_bosses)
        if not available_bosses_list:
            raise ValueError('No "Special" bosses available to choose (all already used or none configured)')
        selected_boss = random.choice(available_bosses_list)

        project_boss_model = ProjectBoss.objects.create(project=self._project.project, boss=selected_boss, hp=self.BASE_SPECIAL_BOSS_HP, max_hp=self.BASE_SPECIAL_BOSS_HP, status="Alive")

        self._boss = None
        return project_boss_model


    def player_attack(self, player_id, task):
        """
        player_id : ID of the player who attacks
        task : Task that player use to attack boss (Task domain object)
        """       
        player = self._project_member_management.get_member(player_id)
        if not player :
            raise ValueError("user not exist in this project")

        if player.status == "Dead":
            raise ValueError("user is dead")
       
        if task.task_id not in {t.task_id for t in self._task_management.tasks}:
            raise ValueError("Task does not belong to the project")            

        if not task.is_completed():
            raise ValueError("Task is not completed")
        
        effects = player.effects()

        time_left = task.deadline - timezone.now()
        time_left_percent = time_left / (task.deadline - task.created_at) 
        
        damage = self.BASE_PLAYER_DAMAGE * (task.priority /time_left_percent)
        # buff or debuff effect

        for user_effect in effects:
            if user_effect.effect.effect_type == "DAMAGE_BUFF":
                damage = damage + (user_effect.effect.value * damage) 
                # one-time effects are consumed on attack
                player.clear_effect(user_effect)
            elif user_effect.effect.effect_type == "DAMAGE_DEBUFF":
                damage = damage - (user_effect.effect.value * damage)
                # one-time effects are consumed on attack
                player.clear_effect(user_effect)

        score = damage * self.BASE_SCORE
        player.score = player.score + score
        self.boss.attacked(damage)

        log = TaskLog.objects.create(
                project_member=player.project_member,
                project_boss=self.boss.project_boss,
                action_type="USER",
                damage_point=damage,
                score_change=score,
                event="ATTACK_BOSS"
            )
        
        if self.boss.hp <= 0:
            if self.boss.type == "normal":
                next_boss = self.next_phase_boss_setup() 
                if next_boss is None:
                    self.boss.die()
                    log = TaskLog.objects.create(
                        project_member=player.project_member,
                        project_boss=self.boss.project_boss,
                        action_type="USER",
                        damage_point=damage,
                        score_change=score,
                        event="KILL_BOSS"
                    )
            else:
                self.boss.die()
                log = TaskLog.objects.create(
                    project_member=player.project_member,
                    project_boss=self.boss.project_boss,
                    action_type="USER",
                    damage_point=damage,
                    score_change=score,
                    event="KILL_BOSS"
                )
        
        
        # attacklog = UserAttack.object.create(
        #     project_member=player,
        #     damage_point=damage,
        #     project_boss=self._boss.project_boss
        # )
        
        return {
            "player_id": player_id,
            "task_id": task.task_id,
            "damage": damage,
            "score": score,
            "boss_hp": self._boss.hp,
            "boss_max_hp": self._boss.max_hp
        } 

    def boss_attack(self, task):
        """
        task: Task that the boss attacks with (Task domain object)
        effect: Buff or Debuff effect on the attack (Event model object)
        """
        target_players = task.get_assigned_members()
        if not target_players:
            raise ValueError("No players assigned to this task")
        
        if task.is_completed():
            raise ValueError("Task is completed")
        
        damage = self.BASE_BOSS_DAMAGE * (task.priority)

        attacked_players =  []

        for player in target_players:
            if player.status == "Dead":
                continue
            effects = player.effects()
            for user_effect in effects:
                if user_effect.effect.effect_type == "DEFENCE_BUFF":
                    damage = damage - (user_effect.effect.value * damage)
                    # one-time effects are consumed on attack
                    player.clear_effect(user_effect)
                elif user_effect.effect.effect_type == "DEFENCE_DEBUFF":
                    damage = damage + (user_effect.effect.value * damage)
                    # one-time effects are consumed on attack
                    player.clear_effect(user_effect)
            player.attacked(damage)
            attacked_players.append({"player_id": player.project_member_id, "damage": damage, "hp": player.hp, "max_hp": player.max_hp  })
            attack_log = TaskLog.objects.create(
                project_boss=self.boss.project_boss,
                project_member=player.project_member,
                action_type="BOSS",
                event="ATTACK_PLAYER",
                damage_point=damage,
            )

            if player.hp <= 0 :
                player.die()
                kill_log = TaskLog.objects.create(
                    project_boss=self.boss.project_boss,
                    project_member=player.project_member,
                    action_type="BOSS",
                    event="KILL_PLAYER",
                    damage_point=damage,
                )
    
        
        # boss_attack_log = BossAttack.objects.create(
        #     project_boss=self._boss.project_boss,
        #     damage_point=damage,
        #     project_member=player
        # )
        return {
            "task_id": task.task_id,
            "attacked_players": attacked_players
        }
    
    def player_support(self, report_domain):
        """
        Apply "support" from a review/report to one or more receivers.

        - **Receives**: `report_domain` (expected to be `api.domains.report.Report` or a Report model-like object)
        - **Uses**: review-domain score logic (`Review.calculate_player_score(...)`) to calculate score delta
        - **Applies**: score gain to receiver(s)
        """
        if report_domain is None:
            raise ValueError("report_domain is required")

        task = self._task_management.get_task(report_domain.task_id)
        if task is None:
            raise ValueError("report_domain.task is required")
       

        facts = TaskFacts(
            priority= task.priority,
            created_at_ts= task.created_at,
            completed_at_ts= task.completed_at,
            deadline_ts= task.deadline
        )

        # Determine receivers
        receivers = task.get_assigned_members()

        # --- Score calculation (use Review domain method only) ---
        reporter_score = self._review.calculate_player_score(facts, report_domain.sentiment_score)

        reporter = report_domain.reporter
        reporter.score += reporter_score

        applied = []
        for receiver in receivers:
            # Only apply to living players (game rules align with heal/attack methods).
            if getattr(receiver, "status", None) == "Dead":
                applied.append(
                    {
                        "receiver_id": str(receiver.project_member_id),
                        "applied": False,
                        "reason": "receiver is dead",
                    }
                )
                continue
            # effect recieve
            effect = self._review.decide_effect(facts, report_domain.sentiment_score)
            # random whether user recieve item or effect
            choice = ["effect", "item"]
            rand_choice = random.choice(choice)
            item = Item.object.get(effect=effect)
            if item == None:
                rand_choice = "effect"
            if rand_choice == "item":
                user_item = UserItem.objects.create(
                    project_member=receiver,
                    item=item)

                #Todo: add log for give item action here after refactor log schema

                applied.append(
                    {
                        "receiver_id": str(receiver.project_member_id),
                        "applied": True,
                        "type" : "item",                        
                        "recieved" : user_item.user_item_id
                    }
                )
            else: 
                userEffect = UserEffect.objects.create(
                    project_member=receiver,
                    effect=effect)
                
                #Todo: add log for give buff/debuff action here after refactor log schema
                applied.append(
                    {
                        "receiver_id": str(receiver.project_member_id),
                        "applied": True,
                        "type" : "effect",                        
                        "recieved" : userEffect.user_item_id
                    }
                )

        return {
            "report_id": report_domain.report_id,
            "reporter" : {
                            "reporter_id" : str(reporter.project_member_id),
                            "score_recieve" : reporter_score,
                            "total_score" : reporter.score
                        },
            "applied": applied,
        }

    def player_heal(self, Healer_id, player_id, heal_value):
        """
        healer_id : ID of the player who performs the heal
        player_id : ID of the player who heals
        heal_value : amount of health to restore

        """
        player = self._project_member_management.get_member(player_id)
        healer = self._project_member_management.get_member(Healer_id)
        if not player :
            raise ValueError("user not exist in this project")

        if player.status == "Dead":
            raise ValueError("player is dead")
        
        if healer.status == "Dead":
            raise ValueError("healer is dead")

        player.heal(heal_value)

        player.score = player.score + (heal_value * self.BASE_SCORE)

        log = TaskLog.objects.create(
                project_member=healer,
                received_project_member=player,
                action_type="USER",
                score_change = heal_value * self.BASE_SCORE,
                event="PLAYER_HEALED"
            )
        
        return {
            "healer_id": Healer_id,
            "player_id": player_id,
            "hp": player.hp,
            "max_hp": player.max_hp
        }
    
    def player_revive(self, player_id):
        player = self._project_member_management.get_member(player_id)
        if player.status == "Alive":
            raise ValueError("player is currently Arrive")
        player.score = player.score/2
        player.hp = player.max_hp
        player.status = "Alive"

    


      