class Boss:
    def __init__(self, boss_model):
        self._boss = boss_model


    @property
    def project_boss(self):
        return self._boss

    @property
    def hp(self) -> int:
        return self._boss.hp

    @property
    def max_hp(self) -> int:
        return self._boss.max_hp

    @property
    def status(self) -> bool:
        return self._boss.status

    @hp.setter
    def hp(self, value: int):
        if value < 0:
            raise ValueError("Boss HP cannot be negative")

        if value > self.max_hp:
            raise ValueError("Boss HP cannot exceed max_hp")

        self._boss.hp = value
        self._boss.save(update_fields=["hp"])

    @max_hp.setter
    def max_hp(self, value: int):
        if value <= 0:
            raise ValueError("Boss max_hp must be greater than 0")

        # keep HP valid when max_hp changes
        if self.hp > value:
            self._boss.hp = value

        self._boss.max_hp = value
        self._boss.save(update_fields=["max_hp", "hp"])
    
    @property
    def boss(self):
        return self._boss.boss
    @boss.setter
    def boss(self, value):
        self._boss.boss = value
        self._boss.save(update_fields=["boss"])

    @property
    def name(self):
        return self._boss.boss.boss_name
    
    @property
    def image(self):
        return self._boss.boss.boss_image
    
    @property
    def updated_at(self):
        return self._boss.updated_at
    @updated_at.setter
    def updated_at(self, value):
        self._boss.updated_at = value
        self._boss.save(update_fields=["updated_at"])


    def attacked(self, damage):
        new_hp = self.hp - damage
        if new_hp < 0:
            new_hp = 0
        self.hp = new_hp