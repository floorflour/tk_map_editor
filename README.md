# tk地图编辑器

## 如何运行

### 使用python

1. 安装Python 3.10
2. 安装pyside6
4. 运行以下命令：

    ```bash
    python map.py
    ```

### 使用可执行文件

在release中下载可执行文件

## 功能介绍

### 基础功能

- 在上方输入地图原始文本

  - 原始文本中的节点会被解析为**城市**或者中继点

  - **城市**由任意连续文字表示
  - **中继点**由◇表示
  - 每次更新后，会自动识别城市和中继点，并允许为这些内容输入相关信息

- 点击更新渲染到下方

  - 每次更新时，之前已经记录的城市的相关信息不会重置
  - 每次更新时，坐标（x行y列）没有变动的中继点的相关信息不会重置

- 点击折叠将输入框隐藏/显示

- 使用ctrl+滚轮调整界面大小

![Alt Text](https://pic.superbed.cc/item/67a29c11fa9f77b4dc80c6e6.gif)

### 连接节点

- 左键点击一个节点，进入**选中模式**
  - **选中模式**下，**主节点**会用绿色显示
  - 此时点击**其他节点**，其他节点会在红色/无色之间切换表示，表示连接/无连接
- 再次左键点击主节点，或者右键点击任意位置退出**选中模式**
- **中继点**的默认名称“◇”会在首次有两个相邻节点时自动变化

![Alt Text](https://pic.superbed.cc/item/67a29c11fa9f77b4dc80c6dc.gif)

### 修改属性

- 进入**选中模式**后，可以再在下方修改其全名，经济值，防御值
  - 会随时保存

![Alt txt](https://pic.superbed.cc/item/67a29c11fa9f77b4dc80c6d5.gif)

### 导出项目

- 点击文件-导出，将项目导出到erb文件
  - 如果有**中继点**的名称依然为默认名称，则会产生警告（该警告说明有中继点没有连接超过两个其他节点）

![Alt txt](https://pic.superbed.cc/item/67a29c11fa9f77b4dc80c6f5.gif)

### 导入项目

- 点击文件-导入，将erb文件导入到程序中
  - 以该程序导出的erb文件和MAP_DEFAULT.erb为标准模板解析

![Alt txt](https://pic.superbed.cc/item/67a29c11fa9f77b4dc80c6d2.gif)
