#
# ------------------------------------------------------------------
#  节点类
# ------------------------------------------------------------------
#

class MapNode:
    """任意节点（城市或中继）的基类。"""
    def __init__(self, name: str, position=None):
        self.name = name.strip()
        self.full_name = self.name
        self.economy = 10000
        self.guard = 100
        self.node_id = 0
        self.connections = set()
        self.position = position  # (行号, 列号)
    def __repr__(self):
        return f"{self.__class__.__name__}(id={self.node_id}, name='{self.name}')"


class CityNode(MapNode):
    """城市节点。"""
    pass


class RelayNode(MapNode):
    """
    中继节点，用于存储中继序号，并显示特殊的符号（例如 '◇'）。
    增加了 position 属性，用于记录所在行和起始列。
    """
    def __init__(self, name: str, position=None):
        super().__init__(name,position)


    def update_full_name_if_two_cities(self):
        """若正好连接两个城市，则将全名更新为 CityA-CityB。"""
        if self.name != "◇":
            return
        city_list = [n for n in self.connections if isinstance(n, CityNode)]
        if len(city_list) == 2:
            self.full_name = f"{city_list[0].full_name}-{city_list[1].full_name}"

