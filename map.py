import os
import sys
import re

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QTextEdit,
    QMenuBar, QMenu, QLabel, QLineEdit, QPushButton, QHBoxLayout,
    QMessageBox, QInputDialog, QFileDialog
)
from PySide6.QtGui import QAction, QFont
from node import MapNode, CityNode, RelayNode
from browser import ClickableMapBrowser
#
# ------------------------------------------------------------------
#  主窗口
# ------------------------------------------------------------------
#

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("tk地图制作器 v1.2")

        # 数据结构
        self.lines = []             # 原始文本行
        self.nodes_by_line = []     # 每行中的节点（城市或中继）
        self.all_nodes = []         # 当前使用的所有节点
        self.max_city_id = 0

        # 当前选中的节点及其高亮的相邻节点
        self.selected_node = None
        self.highlighted_nodes = set()

        # 构建UI
        self._setupMenuBar()
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        central.setLayout(main_layout)

        # 1) 文本输入（ASCII地图）
        self.input_area = QTextEdit()
        self.input_area.setFont(QFont("MS Gothic", 10))
        main_layout.addWidget(self.input_area)

        # 2) 更新按钮（只有点击后才将输入转换为显示）
        self.update_button = QPushButton("更新")
        self.update_button.clicked.connect(self.on_update_pressed)
        main_layout.addWidget(self.update_button)

        # 3) 折叠/展开输入区域按钮
        self.toggle_input_button = QPushButton("折叠输入")
        self.toggle_input_button.clicked.connect(self.on_toggle_input)
        main_layout.addWidget(self.toggle_input_button)

        # 4) 显示区域（只读HTML地图），内容居中
        self.display_area = ClickableMapBrowser(self)
        self.display_area.setStyleSheet("QTextBrowser { font-family: 'MS Gothic'; }")
        main_layout.addWidget(self.display_area)

        # 5) 行：全名、经济、防御
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("全名:"))
        self.full_name_edit = QLineEdit()
        row2.addWidget(self.full_name_edit)

        row2.addWidget(QLabel("经济:"))
        self.economy_edit = QLineEdit()
        row2.addWidget(self.economy_edit)

        row2.addWidget(QLabel("防御:"))
        self.guard_edit = QLineEdit()
        row2.addWidget(self.guard_edit)

        main_layout.addLayout(row2)

        # 当这些字段改变时，更新节点数据
        self.full_name_edit.textEdited.connect(self.on_full_name_changed)
        self.economy_edit.textEdited.connect(self.on_economy_changed)
        self.guard_edit.textEdited.connect(self.on_guard_changed)

        self.resize(1100, 800)

    #
    # 菜单栏：导出
    #
    def _setupMenuBar(self):
        menubar = QMenuBar(self)
        file_menu = QMenu("文件", self)
        menubar.addMenu(file_menu)

        export_action = QAction("导出", self)
        export_action.triggered.connect(self.export_data)
        file_menu.addAction(export_action)

        import_action = QAction("导入", self)
        import_action.triggered.connect(self.import_data)
        file_menu.addAction(import_action)
        self.setMenuBar(menubar)

    #
    # 点击“更新”按钮后调用
    #
    def on_update_pressed(self):
        self.selected_node = None
        self.highlighted_nodes = set()
        self._parse_input()
        self._update_display_and_fields()

    #
    # 点击“折叠输入”按钮后调用
    #
    def on_toggle_input(self):
        visible = self.input_area.isVisible()
        self.input_area.setVisible(not visible)
        self.toggle_input_button.setText("展开输入" if visible else "折叠输入")

    #
    # 解析输入文本，构建节点数据结构
    #
    def _parse_input(self):
        """
        解析输入文本，并重用已有节点（城市按名称，中继按位置）。
        同时严格按规则分配ID：
          - 城市从左到右、从上到下依次编号（1,2,3...）
          - 中继从城市最大ID+1开始编号
        """
        text = self.input_area.toPlainText()
        new_lines = text.split('\n')
        new_nodes_by_line = []
        new_all_nodes: list[MapNode] = []

        # 构造旧节点映射以便复用
        old_city_mapping = {}
        old_relay_mapping = {}
        for node in self.all_nodes:
            if isinstance(node, CityNode):
                old_city_mapping.setdefault(node.name, []).append(node)
            elif isinstance(node, RelayNode) and getattr(node, 'position', None) is not None:
                old_relay_mapping[node.position] = node

        # 匹配城市和中继节点,只读取◇或者连续的文字
        node_pattern = re.compile(r'([a-zA-Z0-9\u4e00-\u9fa5]+)|(◇)')

        city_id = 1
        relay_nodes_temp = []  # 临时保存中继节点，稍后分配ID
        for line_index, line in enumerate(new_lines):
            line_entries = []
            last_end = 0
            for match in node_pattern.finditer(line):
                start_index = match.start()
                if start_index > last_end:
                    # 文本部分
                    text_part = line[last_end:start_index]
                    line_entries.append(('text', text_part))
                token = match.group(0)
                if match.group(1):  # 城市
                    # 尝试复用同名城市节点
                    if token in old_city_mapping and old_city_mapping[token]:
                        node_obj = old_city_mapping[token].pop(0)
                    else:
                        node_obj = CityNode(token)
                    node_obj.name = token.strip()
                    if not node_obj.full_name:
                        node_obj.full_name = node_obj.name
                    node_obj.node_id = city_id
                    city_id += 1
                    line_entries.append(('city', node_obj))
                    new_all_nodes.append(node_obj)
                elif match.group(2):  # 中继
                    pos_key = (line_index, start_index)
                    if pos_key in old_relay_mapping:
                        node_obj = old_relay_mapping[pos_key]
                    else:
                        node_obj = RelayNode(token, position=pos_key)
                    line_entries.append(('relay', node_obj))
                    relay_nodes_temp.append(node_obj)
                last_end = match.end()
            if last_end < len(line):
                line_entries.append(('text', line[last_end:]))
            new_nodes_by_line.append(line_entries)

        # 分配中继节点ID：从城市ID结束后开始
        relay_id = city_id
        for line_entries in new_nodes_by_line:
            for entry in line_entries:
                if entry[0] == 'relay':
                    entry[1].node_id = relay_id
                    relay_id += 1

        self.max_city_id = city_id - 1 if city_id > 1 else 0

        # 合并中继节点（避免重复添加）
        for relay_node in relay_nodes_temp:
            if relay_node not in new_all_nodes:
                new_all_nodes.append(relay_node)

        # 更新每个节点的 connections：只保留出现在新_all_nodes中的连接
        new_set = set(new_all_nodes)
        for node in new_all_nodes:
            node.connections = {conn for conn in node.connections if conn in new_set}

        # 更新数据结构
        self.lines = new_lines
        self.nodes_by_line = new_nodes_by_line
        self.all_nodes = new_all_nodes

    #
    # 构建带锚点和样式的HTML，内容居中
    #
    def _build_html(self) -> str:
        lines_html = []
        for line_entries in self.nodes_by_line:
            line_parts = []
            for entry in line_entries:
                if entry[0] == 'text':
                    processed_text = entry[1].replace(' ', '&nbsp;')
                    line_parts.append(f'<span style="white-space: pre;">{processed_text}</span>')
                elif entry[0] in ('city', 'relay'):
                    node = entry[1]
                    display_text = node.name if isinstance(node, CityNode) else '◇'
                    # 添加悬浮提示信息
                    tooltip = (f"名称: {node.name}\n"
                               f"全名: {node.full_name}\n"
                               f"经济: {node.economy}\n"
                               f"防御: {node.guard}\n"
                               f"相邻: {', '.join(n.name for n in node.connections)}")
                    anchor = f'<a name="node_{node.node_id}"></a>'
                    style = [
                        "color: black",
                        "font-family: 'MS Gothic'",
                        "text-decoration: none",
                        "padding: 0",
                        "margin: 0"
                    ]
                    # 选中节点高亮绿色显示
                    if node == self.selected_node:
                        style.append("background: lightgreen")
                    # 相邻节点高亮粉色显示
                    elif node in self.highlighted_nodes:
                        style.append("background: pink")
                    link = f'<a title="{tooltip}" href="node_{node.node_id}" style="{";".join(style)}">{display_text}</a>'
                    line_parts.append(anchor + link)
            lines_html.append(f'<div style="white-space: pre-wrap;">{"".join(line_parts)}</div>')

        return f'''
        <html>
        <head>
        <style>
            body {{
                font-family: 'MS Gothic';
                color: black;
                background-color: white;
                margin: 0;
                padding: 0;
                -webkit-touch-callout: none;
                -webkit-user-select: none;
                -moz-user-select: none;
                -ms-user-select: none;
                user-select: none;
            }}
        </style>
        </head>
        <body>
        {"".join(lines_html)}
        </body>
        </html>
        '''

    #
    # 更新显示和输入框状态
    #
    def _update_display_and_fields(self):
        html = self._build_html()
        self.display_area.setHtml(html)
        if self.selected_node:
            self.full_name_edit.setText(self.selected_node.full_name)
            self.economy_edit.setText(str(self.selected_node.economy))
            self.guard_edit.setText(str(self.selected_node.guard))
        else:
            self.full_name_edit.clear()
            self.economy_edit.clear()
            self.guard_edit.clear()
            self.full_name_edit.setReadOnly(False)

    #
    # 右键点击事件：取消选中节点
    #
    def on_right_click(self):
        self.selected_node = None
        self.highlighted_nodes = set()
        self._update_display_and_fields()

    #
    # 处理地图锚点点击事件，绑定状态保持
    #
    def on_map_anchor_clicked(self, node: MapNode):
        # 点击节点时，如果当前没有选中节点，则选中当前节点并高亮相邻节点
        if self.selected_node is None:
            self.selected_node = node
            self.highlighted_nodes = node.connections.copy()
            self.highlighted_nodes.add(node)
        elif self.selected_node == node:
            # 再次点击当前选中节点则退出绑定状态
            self.selected_node = None
            self.highlighted_nodes = set()
        else:
            # 点击其他节点时建立或取消连接，但保持当前选中状态
            if node in self.selected_node.connections:
                self.selected_node.connections.remove(node)
                node.connections.remove(self.selected_node)
            else:
                self.selected_node.connections.add(node)
                node.connections.add(self.selected_node)
                if isinstance(self.selected_node, RelayNode):
                    self.selected_node.update_full_name_if_two_cities()
                if isinstance(node, RelayNode):
                    node.update_full_name_if_two_cities()
            self.highlighted_nodes = self.selected_node.connections.copy()
            self.highlighted_nodes.add(self.selected_node)

        self._update_display_and_fields()

    #
    # 更新节点属性 全名 经济 防卫
    #
    def on_full_name_changed(self, txt):
        if isinstance(self.selected_node, MapNode):
            self.selected_node.full_name = txt
            self._update_display_and_fields()

    def on_economy_changed(self, txt):
        if self.selected_node and txt.isdigit():
            self.selected_node.economy = int(txt)
        self._update_display_and_fields()

    def on_guard_changed(self, txt):
        if self.selected_node and txt.isdigit():
            self.selected_node.guard = int(txt)
        self._update_display_and_fields()

    #
    # 导出数据：先弹出输入框获取MAPID（默认为NEW MAP），
    # 后续输出中将所有MAPID替换为用户输入的内容
    #
    def export_check_relay(self)->bool:
        # 预先检查每个中继点，如果其名称仍为菱形，则触发警告
        warnings = []
        for line_index, line_entries in enumerate(self.nodes_by_line):
            relay_index = 0  # 用于记录当前行中第几个中继点
            for entry in line_entries:
                if entry[0] == 'relay':
                    relay_index += 1
                    relay_node = entry[1]
                    if relay_node.full_name == "◇":
                            warnings.append(f"位于第 {line_index+1} 行第 {relay_index} 个中继点仍然为默认名称")
        if warnings:
            # 最多显示10行
            display_warnings = warnings[:10]
            if len(warnings) > 10:
                display_warnings.append("...")
            msg = "\n".join(display_warnings) + "\n是否继续导出？"
            reply = QMessageBox.question(self, "警告", msg, QMessageBox.Yes | QMessageBox.No)
            return reply == QMessageBox.Yes
        return True

    def export_data(self):
        # 弹出输入框，获取MAPID（必须全英文，默认"NEWMAP"）
        mapid, ok = QInputDialog.getText(self, "输入MAPID", "请输入MAPID:", text="NEWMAP")
        if not ok:
            return
        keep_gen = self.export_check_relay()
        if not keep_gen:
            return
        # 生成导出内容
        output_lines = []
        output_lines.append(";==== Export Start ====")
        output_lines.append(f"@DRAWMAP_{mapid}(ARG:0 = 0, ARG:1 = 0)")
        output_lines.append("""CALL DRAWMAP_INIT(ARG:0, 0)
    ;MAP_SHOW_TYPE
    IF DRAWMAP_MENUBARTYPE != 0
        CALL DRAWMAP_PRINT_MENU(DRAWMAP_MENUBARTYPE, DRAWMAP_LINECOUNT)
        DRAWMAP_LINECOUNT++
        CALL DRAW_MAP_SHOW_CONFIG_BUTTON()
    ELSE
        MAP_SHOW_CONFIG = 0
    ENDIF""")
        for i, line_text in enumerate(self.lines):
            line_entries = self.nodes_by_line[i]
            ids_in_line = [str(entry[1].node_id) for entry in line_entries if entry[0] in ('city', 'relay')]
            joined_ids = ",".join(ids_in_line)
            safe_line_text = line_text.replace('"', '\\"')
            output_lines.append(f'CALL DRAWMAP_LINE("{safe_line_text}", {joined_ids})')
        output_lines.append("CALL DRAWMAP_END()")
        output_lines.append("")
        output_lines.append(f"@SET_CITY_NUM_{mapid}()")
        output_lines.append(f"CITY_NUM = {self.max_city_id}")
        output_lines.append("")
        output_lines.append(f"@SET_SHORTCITYNAME_{mapid}()")
        for node in self.all_nodes:
            if isinstance(node, CityNode):
                output_lines.append(f"CITY_NAME_SHORT:{node.node_id} = {node.name}")
        output_lines.append("""FOR LOCAL:0, 0, MAX_CITY
        SIF CITY_TYPE:(LOCAL:0) == 1
            CITY_NAME_SHORT:(LOCAL:0) = ●
    NEXT
    """)
        output_lines.append("")
        output_lines.append(f"@SET_CITYNAME_{mapid}()")
        output_lines.append("VARSET CITY_NAME,\"無名\"")
        for node in self.all_nodes:
            if isinstance(node, CityNode):
                output_lines.append(f"CITY_NAME:{node.node_id} = {node.full_name}")
        for node in self.all_nodes:
            if isinstance(node, RelayNode):
                output_lines.append(f"CITY_NAME:{node.node_id} = {node.full_name}")

        output_lines.append(f"@SET_CITY_TYPE_{mapid}")
        output_lines.append("""
    FOR LOCAL:0, GET_CITY_NUM() + 1, MAX_CITY
        CITY_TYPE:(LOCAL:0) = 1
    NEXT
    """)
        output_lines.append("")
        output_lines.append(f"@SET_MAP_ROUTE_{mapid}")
        for node in self.all_nodes:
            sorted_conns = sorted(node.connections, key=lambda x: x.node_id)
            if sorted_conns:
                names = [c.full_name for c in sorted_conns]
                all_args = '", "'.join(names)
                output_lines.append(f'CALL REGISTER_ROUTE_S("{node.full_name}", "{all_args}")')
            else:
                output_lines.append(f'CALL REGISTER_ROUTE_S("{node.full_name}")')
        output_lines.append("")
        output_lines.append(f"@MAP_INIT_{mapid}")
        for node in self.all_nodes:
            if isinstance(node, CityNode):
                output_lines.append(f'CITY_ECONOMY:GET_CITYNUMBER("{node.full_name}") = {node.economy}')
        output_lines.append("""
    FOR LOCAL:0, 1, MAX_CITY
        CITY_ECONOMY_LIMIT:(LOCAL:0) = MIN(CITY_ECONOMY:(LOCAL:0) * 2, 300000)
    NEXT
    """)
        for node in self.all_nodes:
            if isinstance(node, CityNode):
                output_lines.append(f'CITY_GUARD:GET_CITYNUMBER("{node.full_name}") = {node.guard}')
        output_lines.append(";==== Export End ====")
        self.export_data_2_file(output_lines, mapid)

    def export_data_2_file(self, output_lines, mapid):
        # 查找可用的文件名
        file_index = 1
        while True:
            file_name = f"MAP_{mapid}_{file_index}.erb"
            if not os.path.exists(file_name):
                break
            file_index += 1

        # 将内容写入文件
        try:
            with open(file_name, "w", encoding="utf-8") as f:
                for line in output_lines:
                    f.write(line + "\n")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"写入文件时出错: {e}")
            return

        # 导出成功后提示用户
        QMessageBox.information(self, "导出完成", f"地图数据已成功导出到 {file_name} 文件中。")

    #
    #导入数据
    #
    def import_data(self):
        # 打开文件对话框，选择要导入的文件
        file_name, _ = QFileDialog.getOpenFileName(self, "选择地图文件", "", "ERB 文件 (*.erb);;所有文件 (*)")
        if not file_name:
            return

        try:
            with open(file_name, "r", encoding="utf-8") as file:
                lines = file.readlines()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"读取文件时出错: {e}")
            return

        # 初始化存储数据的变量
        map_lines = []       # 存放每行地图文本和对应节点 ID 列表的元组 [(text, [node_id, ...]), ...]
        city_names = {}      # 从 CITY_NAME_SHORT: 行中解析到的数据 {node_id: short_name}
        city_full_names = {} # 从 CITY_NAME: 行中解析到的数据 {node_id: full_name}
        city_economy = {}    # 从 CITY_ECONOMY: 行中解析到的数据 {full_name: economy}
        city_guard = {}      # 从 CITY_GUARD: 行中解析到的数据 {full_name: guard}
        connections = {}     # 从 CALL REGISTER_ROUTE_S 行中解析到的数据 {full_name: [connected_full_name, ...]}

        # 遍历每一行进行解析
        for line in lines:
            line = line.strip()
            if line.startswith('CALL DRAWMAP_LINE'):
                # 解析地图行，提取文本和节点 ID 列表
                match = re.match(r'CALL DRAWMAP_LINE\("(.+?)",\s*(.*?)\)', line)
                if match:
                    text, ids = match.groups()
                    text = text.replace('\\"', '"')  # 恢复转义的引号
                    id_list = [int(id_) for id_ in ids.split(',') if id_]
                    map_lines.append((text, id_list))
            elif line.startswith('CITY_NAME_SHORT:'):
                # 解析简短名称（节点名称）
                match = re.match(r'CITY_NAME_SHORT:(\d+)\s*=\s*(.+)', line)
                if match:
                    node_id, name = match.groups()
                    city_names[int(node_id)] = name.strip()
            elif line.startswith('CITY_NAME:'):
                # 解析全名
                match = re.match(r'CITY_NAME:(\d+)\s*=\s*(.+)', line)
                if match:
                    node_id, full_name = match.groups()
                    city_full_names[int(node_id)] = full_name.strip()
            elif line.startswith('CITY_ECONOMY:'):
                # 解析经济值
                match = re.match(r'CITY_ECONOMY:GET_CITYNUMBER\("(.+?)"\)\s*=\s*(\d+)', line)
                if match:
                    full_name, economy = match.groups()
                    city_economy[full_name] = int(economy)
            elif line.startswith('CITY_GUARD:'):
                # 解析防御值
                match = re.match(r'CITY_GUARD:GET_CITYNUMBER\("(.+?)"\)\s*=\s*(\d+)', line)
                if match:
                    full_name, guard = match.groups()
                    city_guard[full_name] = int(guard)
            elif line.startswith('CALL REGISTER_ROUTE_S'):
                # 解析连接关系，提取所有双引号内的内容
                names = re.findall(r'"([^"]+)"', line)
                if names:
                    node_full_name = names[0]  # 第一个为当前节点的全名
                    connections[node_full_name] = names[1:]  # 后续为相连节点的全名

        # 根据 full_name 和短名称构建节点对象
        self.all_nodes.clear()
        node_map = {}
        # 所有节点 ID 的并集（key 均为节点的 id）
        all_node_ids = set(city_full_names.keys()).union(set(city_names.keys()))
        for node_id in sorted(all_node_ids):
            short_name = city_names.get(node_id)   # 可能为 None
            # 优先从 CITY_NAME 中获取 full_name，若不存在则使用 short_name
            full_name = city_full_names.get(node_id, short_name)
            # 根据要求：以 full_name 为基础，如果 short_name 不存在或为默认中继符号 "◇"，则认为该节点为中继节点
            if not short_name or short_name == "◇":
                node = RelayNode("◇", position=None)
            else:
                node = CityNode(short_name)
            node.node_id = node_id
            node.full_name = full_name
            node.economy = city_economy.get(full_name, 0)
            node.guard = city_guard.get(full_name, 0)
            node_map[full_name] = node
            self.all_nodes.append(node)

        # 恢复连接关系（使用 full_name 作为标识，要求导出时 full_name 唯一）
        for node_full_name, conn_full_names in connections.items():
            node = node_map.get(node_full_name)
            if node:
                for conn_full_name in conn_full_names:
                    conn_node = node_map.get(conn_full_name)
                    if conn_node:
                        node.connections.add(conn_node)
                        conn_node.connections.add(node)

        # 更新输入区域文本为导入的地图文本
        imported_text = "\n".join([item[0] for item in map_lines])
        self.input_area.setPlainText(imported_text)

        # 为每个节点添加坐标，确保 _parse_input 中可以正确复用原有节点
        # 这里使用与 _parse_input 中相同的正则表达式（匹配城市名称和中继符号 "◇"）
        node_pattern = re.compile(r'([a-zA-Z0-9\u4e00-\u9fa5]+)|(◇)')
        lines_in_text = imported_text.splitlines()
        for line_index, line in enumerate(lines_in_text):
            matches = list(node_pattern.finditer(line))
            # 根据 map_lines 中保存的节点 ID 顺序，为本行中每个节点分配坐标
            if line_index < len(map_lines):
                ids_in_line = map_lines[line_index][1]
                for token_index, match in enumerate(matches):
                    if token_index < len(ids_in_line):
                        node_id = ids_in_line[token_index]
                        # 在 self.all_nodes 中找到对应节点，并记录其位置（行号, 列起始位置）
                        for node in self.all_nodes:
                            if node.node_id == node_id:
                                node.position = (line_index, match.start())
                                break

        # 调用更新方法，重新解析输入文本，构建节点数据结构
        self.on_update_pressed()

        QMessageBox.information(self, "导入完成", f"地图数据已成功从 {file_name} 导入。")

#
# ------------------------------------------------------------------
#  主函数
# ------------------------------------------------------------------
#

def main():
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
