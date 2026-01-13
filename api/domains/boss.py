from Backend.api.domains.boss import Boss
import rest_framework
class Boss:
    def __init__(self, boss_model):
        self._boss = boss_model

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


    