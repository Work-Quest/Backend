
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
            raise ValueError("Boss HP cannot be negative")

        if value > self.max_hp:
            raise ValueError("Boss HP cannot exceed max_hp")

        self._member.hp = value
        self._member.save(update_fields=["hp"])

    @property
    def max_hp(self):
        return self._member.max_hp
    
    @max_hp.setter
    def max_hp(self, value: int):
        if value <= 0:
            raise ValueError("Boss max_hp must be greater than 0")

        # keep HP valid when max_hp changes
        if self.hp > value:
            self._member.hp = value

        self._member.max_hp = value
        self._member.save(update_fields=["max_hp", "hp"])

    def delete(self):
        if self._deleted:
            return
        
        self._member.delete()