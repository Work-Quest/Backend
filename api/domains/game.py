from api.models.ProjectBoss import ProjectBoss
from api.domains.boss import Boss as BossDomain
from api.models.Boss import Boss
import random
from django.utils import timezone
from api.models import TaskLog


class Game:
    def __init__(self, project_domain):
        self._project = project_domain
        self._task_management = project_domain.TaskManagement
        self._project_member_management = project_domain.project_member_management
        self._players = self._project_member_management.members

        self._boss = None

        self.BASE_BOSS_HP = 1000
        self.BASE_PLAYER_DAMAGE = 1000
        self.BASE_BOSS_DAMAGE = 10

        self.BASE_SCORE = 0.1

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
            .last()
        )

        if project_boss is None:
            return None
        self._boss = BossDomain(project_boss)
        return self._boss

    def initail_boss_set_up(self):
        if self.boss:
            raise ValueError("Boss already initialized")
        project_boss_model = ProjectBoss.objects.create(project=self._project.project, boss=None, hp=0, max_hp=0, status="Alive")
        self._boss = BossDomain(project_boss_model)
        all_boss = list(Boss.objects.all())
        selected_boss = random.choice(all_boss)  
        self._boss.boss = selected_boss

        all_tasks = self._task_management.tasks
        boss_hp = sum(task.priority for task in all_tasks) * self.BASE_BOSS_HP
        self._boss.max_hp = boss_hp
        self._boss.full_heal()
        self._boss.updated_at = timezone.now()
        return project_boss_model

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
        self.boss.phrase += 1

        self.boss.updated_at = timezone.now()

        return  self.boss.project_boss
    

    # def special_boss_setup(self, boss: Boss):


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
        damage = 30000
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
        
        log = TaskLog.objects.create(
                project_boss=self.boss.project_boss,
                action_type="BOSS",
                event="ATTACK_PLAYERS",
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
    


      