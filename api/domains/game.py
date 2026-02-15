from api.models.UserItem import UserItem
from api.models.Item import Item
from api.models.UserEffect import UserEffect
from api.models.ProjectBoss import ProjectBoss
from api.domains.boss import Boss as BossDomain
from api.models.Boss import Boss
import random
from django.utils import timezone
from api.models import TaskLog
from api.domains.review import Review
from api.dtos.review_dto import TaskFacts
import math

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

        
        self.BOSS_HP_TUNING = {
            "priority_weight": 1.0,
            "members_weight": 0.5,
        }

        self.BASE_SCORE = 0.1
        self.BASE_SPECIAL_BOSS_HP = 5000
        self.DAMAGE_TUNING = {
            "priority": { "base": 0.4, "weight": 0.8 },   
            "speed":    { "base": 0.6, "weight": 0.9 },
        }

        
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

    def initial_boss_setup(self):
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
        member_count = int(self._project.project.members.count())
        member_count = max(member_count, 1)

        boss_hp_units = (
            (float(self.BOSS_HP_TUNING["priority_weight"]) * float(total_priority))
            + (float(self.BOSS_HP_TUNING["members_weight"]) * float(member_count))
        )
        boss_hp = int(boss_hp_units * self.BASE_BOSS_HP)
        self._boss.max_hp = boss_hp
        self._boss.full_heal()
        self._boss.updated_at = timezone.now()
        return self._boss

    def next_phase_boss_setup(self):
        add_logs = TaskLog.objects.filter(
            project_id=self._project.project.project_id,
            actor_type=TaskLog.ActorType.USER,
            event_type=TaskLog.EventType.TASK_CREATED,
            created_at__gt=self._boss.updated_at,
        )

        delete_logs = TaskLog.objects.filter(
            project_id=self._project.project.project_id,
            actor_type=TaskLog.ActorType.USER,
            event_type=TaskLog.EventType.TASK_DELETED,
            created_at__gt=self._boss.updated_at,
        )

        if not add_logs.exists():
            return None

        add_value = sum(int((log.payload or {}).get("task_priority_snapshot") or 0) for log in add_logs)
        delete_value = sum(int((log.payload or {}).get("task_priority_snapshot") or 0) for log in delete_logs)
        net_change = add_value - delete_value

        # Preserve existing gate: only advance phase if the net task-priority increased.
        if net_change <= 0:
            return None

        member_count = int(self._project.project.members.count())
        member_count = max(member_count, 1)

        boss_hp_units = (
            (float(self.BOSS_HP_TUNING["priority_weight"]) * float(net_change))
            + (float(self.BOSS_HP_TUNING["members_weight"]) * float(member_count))
        )
        hp_change = int(boss_hp_units * self.BASE_BOSS_HP)
        
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
        
        
        # normalize 
        priorityFactor = task.priority / 4
        if time_left_percent >= 0:
            speedFactor = 0.5 + 0.5 * time_left_percent
        else:
            lateness = -time_left_percent
            penalty = math.exp(-2 * lateness)
            speedFactor = 0.5 * penalty

        speedFactor = max(speedFactor, 0.1)
        # weight
        priority_weight = self.DAMAGE_TUNING["priority"]["base"] + self.DAMAGE_TUNING["priority"]["weight"]  * priorityFactor
        time_weight = self.DAMAGE_TUNING["speed"]["base"] + self.DAMAGE_TUNING["speed"]["weight"]  * speedFactor

        damage = self.BASE_PLAYER_DAMAGE * priority_weight * time_weight
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

        TaskLog.write(
            project_id=self._project.project.project_id,
            actor_type=TaskLog.ActorType.USER,
            actor_id=player.project_member_id,
            event_type=TaskLog.EventType.USER_ATTACK,
            payload={
                "task_id": str(task.task_id),
                "damage": int(round(damage)),
                "score_recieve": int(round(score)),
                "boss_hp": int(self.boss.hp),
            },
        )
        
        if self.boss.hp <= 0:
            if self.boss.boss.boss_type == "normal":
                next_boss = self.next_phase_boss_setup() 
                if next_boss is None:
                    self.boss.die()
                    TaskLog.write(
                        project_id=self._project.project.project_id,
                        actor_type=TaskLog.ActorType.USER,
                        actor_id=player.project_member_id,
                        event_type=TaskLog.EventType.KILL_BOSS,
                        payload={"player_id": str(player.project_member_id)},
                    )
            else:
                self.boss.die()
                TaskLog.write(
                    project_id=self._project.project.project_id,
                    actor_type=TaskLog.ActorType.USER,
                    actor_id=player.project_member_id,
                    event_type=TaskLog.EventType.KILL_BOSS,
                    payload={"player_id": str(player.project_member_id)},
                )
        
    
        
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
        
        attacked_players =  []

        for player in target_players:
            if player.status == "Dead":
                continue
            effects = player.effects()
            # Calculate damage per-player so effects don't leak across players.
            damage = self.BASE_BOSS_DAMAGE * (task.priority)
            for user_effect in effects:
                if user_effect.effect.effect_type == "DEFENCE_BUFF":
                    damage = damage - (user_effect.effect.value * damage)
                    # one-time effects are consumed on attack
                    player.clear_effect(user_effect)
                elif user_effect.effect.effect_type == "DEFENCE_DEBUFF":
                    damage = damage + (user_effect.effect.value * damage)
                    # one-time effects are consumed on attack
                    player.clear_effect(user_effect)
            # Never allow negative damage (would heal and can violate domain invariants).
            damage = max(damage, 0)
            player.attacked(damage)
            attacked_players.append({"player_id": player.project_member_id, "damage": damage, "hp": player.hp, "max_hp": player.max_hp  })
            TaskLog.write(
                project_id=self._project.project.project_id,
                actor_type=TaskLog.ActorType.BOSS,
                actor_id=self.boss.project_boss.project_boss_id,
                event_type=TaskLog.EventType.BOSS_ATTACK,
                payload={
                    "task_id": str(task.task_id),
                    "damage": int(round(damage)),
                    "player_hp": int(player.hp),
                },
            )

            if player.hp <= 0 :
                player.die()
                TaskLog.write(
                    project_id=self._project.project.project_id,
                    actor_type=TaskLog.ActorType.BOSS,
                    actor_id=self.boss.project_boss.project_boss_id,
                    event_type=TaskLog.EventType.KILL_PLAYER,
                    payload={"boss_id": str(self.boss.project_boss.project_boss_id)},
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
       

        def _ts(dt):
            return dt.timestamp() if dt is not None else None

        facts = TaskFacts(
            priority=int(task.priority or 1),
            created_at_ts=float(_ts(task.created_at)),
            completed_at_ts=_ts(task.completed_at),
            deadline_ts=_ts(task.deadline),
        )
        trust_scores = self._review.trust_policy.compute(facts, report_domain.sentiment_score)
        weighted_sentiment_score = float(trust_scores.get("weight_sentiment_score"))

        # Determine receivers
        receivers = task.get_assigned_members()

        # --- Score calculation (use Review domain method only) ---
        reporter_score = int(self._review.calculate_player_score(facts, report_domain.sentiment_score))

        reporter = report_domain.reporter
        reporter.score = reporter.score + reporter_score

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
            if effect is None:
                applied.append(
                    {
                        "receiver_id": str(receiver.project_member_id),
                        "applied": False,
                        "reason": "no effect configured",
                    }
                )
                continue
            # random whether user recieve item or effect
            choice = ["effect", "item"]
            rand_choice = random.choice(choice)
            item = None
            if effect is not None:
                item = Item.objects.filter(effects=effect).first()
            if item is None:
                rand_choice = "effect"
            if rand_choice == "item":
                user_item = UserItem.objects.create(
                    project_member=receiver.project_member,
                    item=item)

                def _effect_payload(eff):
                    if eff is None:
                        return None
                    return {
                        "effect_id": str(eff.effect_id),
                        "effect_type": eff.effect_type,
                        "effect_value": eff.value,
                        "effect_polarity": eff.effect_polarity,
                        "effect_description": eff.description,
                    }

                TaskLog.write(
                    project_id=self._project.project.project_id,
                    actor_type=TaskLog.ActorType.USER,
                    actor_id=reporter.project_member_id,
                    event_type=TaskLog.EventType.GIVE_ITEM,
                    payload={
                        "task_id": str(task.task_id),
                        "report_id": str(report_domain.report_id),
                        "effect": _effect_payload(effect),
                        "item": {
                            "item_id": str(item.item_id),
                            "item_name": item.name,
                            "item_description": item.description,
                        },
                        "receiver_id": str(receiver.project_member_id),
                    },
                )

                applied.append(
                    {
                        "reporter_id": str(reporter.project_member_id),
                        "receiver_id": str(receiver.project_member_id),
                        "applied": True,
                        "type" : "item",                        
                        "received" : str(user_item.user_item_id),
                        "item": {
                            "item_id": str(item.item_id),
                            "item_name": item.name,
                            "item_description": item.description,
                        },
                    }
                )
            else: 
                user_effect = UserEffect.objects.create(
                    project_member=receiver.project_member,
                    effect=effect)

                def _effect_payload(eff):
                    if eff is None:
                        return None
                    return {
                        "effect_id": str(eff.effect_id),
                        "effect_type": eff.effect_type,
                        "effect_value": eff.value,
                        "effect_polarity": eff.effect_polarity,
                        "effect_description": eff.description,
                    }

                if effect.effect_type == "HEAL":
                    response = self.player_heal(
                        reporter.project_member_id,
                        receiver.project_member_id,
                        effect.value,
                        task_id=task.task_id,
                        report_id=report_domain.report_id,
                        sentiment_score=report_domain.sentiment_score,
                        weighted_sentiment_score=weighted_sentiment_score,
                    )
                    user_effect.delete()
                    applied.append({
                        "reporter_id": str(reporter.project_member_id),
                        "receiver_id": str(receiver.project_member_id),
                        "applied": True,
                        "type" : "effect",
                        "received" : str(user_effect.user_effect_id),
                        "effect": {
                            "effect_id": str(effect.effect_id),
                            "effect_type": effect.effect_type,
                            "effect_value": effect.value,
                            "effect_polarity": effect.effect_polarity,
                            "effect_description": effect.description,
                        },                       
                        "heal" : response
                    })
                else:
                    event_type = (
                        TaskLog.EventType.APPLY_BUFF
                        if str(effect.effect_polarity).upper() == "GOOD"
                        else TaskLog.EventType.APPLY_DEBUFF
                    )
                    TaskLog.write(
                        project_id=self._project.project.project_id,
                        actor_type=TaskLog.ActorType.USER,
                        actor_id=reporter.project_member_id,
                        event_type=event_type,
                        payload={
                            "task_id": str(task.task_id),
                            "report_id": str(report_domain.report_id),
                            "effect": _effect_payload(effect),
                            "receiver_id": str(receiver.project_member_id),
                        },
                    )
                    applied.append(
                        {
                            "reporter_id": str(reporter.project_member_id),
                            "receiver_id": str(receiver.project_member_id),
                            "applied": True,
                            "type" : "effect",                        
                            "received" : str(user_effect.user_effect_id),
                            "effect": {
                                "effect_id": str(effect.effect_id),
                                "effect_type": effect.effect_type,
                                "effect_value": effect.value,
                                "effect_polarity": effect.effect_polarity,
                                "effect_description": effect.description,
                            }     
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

    def player_heal(
        self,
        Healer_id,
        player_id,
        heal_value,
        *,
        task_id=None,
        report_id=None,
        sentiment_score=None,
        weighted_sentiment_score=None,
    ):
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

        heal_amount = player.max_hp * (heal_value/100)

        player.heal(heal_amount)

        TaskLog.write(
            project_id=self._project.project.project_id,
            actor_type=TaskLog.ActorType.USER,
            actor_id=healer.project_member_id,
            event_type=TaskLog.EventType.HEAL,
            payload={
                "task_id": (str(task_id) if task_id else None),
                "report_id": (str(report_id) if report_id else None),
                "sentiment_score": (int(sentiment_score) if sentiment_score is not None else None),
                "weighted_sentiment_score": (
                    float(weighted_sentiment_score) if weighted_sentiment_score is not None else None
                ),
                "receiver_id": str(player.project_member_id),
                "player_hp": int(player.hp),
            },
        )
        
        return {
            "healer_id": Healer_id,
            "player_id": player_id,
            "hp": player.hp,
            "max_hp": player.max_hp
        }
    

    def player_use_item(self, player_id, item_id):
        """
        Consume a user's owned item and apply its effect.

        Parameters
        - player_id: ProjectMember ID (uuid string)
        - item_id: UserItem ID (uuid string)  (kept as `item_id` for backwards compatibility)
        """
        player = self._project_member_management.get_member(player_id)
        if not player:
            raise ValueError("user not exist in this project")
        if player.status == "Dead":
            raise ValueError("user is dead")

        # item_id is actually the owned UserItem id
        user_item = (
            UserItem.objects
            .select_related("item", "item__effects")
            .get(item_id=item_id, project_member=player.project_member)
        )
        item = user_item.item
        effect = item.effects

        # consume item first (so it can't be used twice)
        user_item.delete()

        def _effect_payload(effect):
            if effect is None:
                return None
            return {
                "effect_id": str(effect.effect_id),
                "effect_type": effect.effect_type,
                "effect_value": effect.value,
                "effect_polarity": effect.effect_polarity,
                "effect_description": effect.description,
            }

        TaskLog.write(
            project_id=self._project.project.project_id,
            actor_type=TaskLog.ActorType.USER,
            actor_id=player.project_member_id,
            event_type=TaskLog.EventType.USE_ITEM,
            payload={
                "task_id": None,
                "report_id": None,
                "effect": _effect_payload(effect),
                "item": {
                    "item_id": str(item.item_id),
                    "item_name": item.name,
                    "item_description": item.description,
                },
                "receiver_id": str(player.project_member_id),
            },
        )

        # item can exist without effects
        if effect is None:
            return {
                "player_id": str(player.project_member_id),
                "item_id": str(item_id),
                "item": {
                    "item_id": str(item.item_id),
                    "item_name": item.name,
                    "item_description": item.description,
                },
                "effect_received": None,
            }

        # HEAL is applied immediately, not stored as a UserEffect
        if effect.effect_type == "HEAL":
            heal_value = int(effect.value)
            if heal_value <= 0:
                raise ValueError("Invalid heal amount")
            response = self.player_heal(player_id, player_id, heal_value)
            return {
                "player_id": str(player.project_member_id),
                "item_id": str(item_id),
                "item": {
                    "item_id": str(item.item_id),
                    "item_name": item.name,
                    "item_description": item.description,
                },
                "effect_received": {
                    "effect_id": str(effect.effect_id),
                    "effect_type": effect.effect_type,
                    "effect_value": effect.value,
                    "effect_polarity": effect.effect_polarity,
                    "effect_description": effect.description,
                },
                "heal": response,
            }

        user_effect = UserEffect.objects.create(project_member=player.project_member, effect=effect)

        return {
            "player_id": str(player.project_member_id),
            "item_id": str(item_id),
            "item": {
                "item_id": str(item.item_id),
                "item_name": item.name,
                "item_description": item.description,
            },
            "effect_received": {
                "user_effect_id": str(user_effect.user_effect_id),
                "effect_id": str(effect.effect_id),
                "effect_type": effect.effect_type,
                "effect_value": effect.value,
                "effect_polarity": effect.effect_polarity,
                "effect_description": effect.description,
            },
        }
    
    def player_revive(self, player_id):
        player = self._project_member_management.get_member(player_id)
        if player.status == "Alive":
            raise ValueError("player is currently Arrive")
        player.score = player.score/2
        player.hp = player.max_hp
        player.status = "Alive"

    


      