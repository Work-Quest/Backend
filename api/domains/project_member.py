from api.models.UserEffect import UserEffect

class ProjectMember:
    def __init__(self, member):
        self._member = member

    @property
    def user(self):
        return self._member.user

    @property
    def project(self):
        return self._member.project
    
    @property
    def project_member_id(self):
        return self._member.project_member_id

    @property
    def status(self):
        return self._member.status
    @status.setter
    def status(self, value):
        self._member.status = value
        self._member.save(update_fields=["status"])

    @property
    def hp(self):
        return self._member.hp
    
    @hp.setter
    def hp(self, value: int):
        if value < 0:
            raise ValueError("Player HP cannot be negative")

        if value > self.max_hp:
            raise ValueError("Player HP cannot exceed max_hp")

        self._member.hp = value
        self._member.save(update_fields=["hp"])

    @property
    def max_hp(self):
        return self._member.max_hp
    
    @max_hp.setter
    def max_hp(self, value: int):
        if value <= 0:
            raise ValueError("Player max_hp must be greater than 0")

        # keep HP valid when max_hp changes
        if self.hp > value:
            self._member.hp = value

        self._member.max_hp = value
        self._member.save(update_fields=["max_hp", "hp"])

    @property
    def score(self):
        return self._member.score
    @score.setter
    def score(self, value: int):
        if value < 0:
            raise ValueError("Player score cannot be negative")

        self._member.score = value
        self._member.save(update_fields=["score"])

    def delete(self):
        self._member.delete()

    def effects(self):
        return list(UserEffect.objects.filter(project_member=self._member))
    
    def applied(self, effect):
        UserEffect.objects.create(
            project_member=self._member,
            effect=effect
        )

    def clear_effect(self, userEffect):
        userEffect.delete()


    def attacked(self, damage):
        new_hp = self.hp - damage
        if new_hp < 0:
            new_hp = 0
        self.hp = new_hp

    def heal(self, heal_amount):
        new_hp = self.hp + heal_amount
        if new_hp > self.max_hp:
            new_hp = self.max_hp
        self.hp = new_hp

  