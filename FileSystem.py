class Node:
    def __init__(self, path):
        self.path = path
        self.name = ''
        # 接下来为三个数组用于表示分块信息
        self.parts = 0
        self.block = []
        self.part_size = []
        self.size = 0
        self.is_dir = False
        # self.children = []

    def get_info(self):
        tmp_block = [str(i) for i in self.block]
        tmp_part_size = [str(i) for i in self.part_size]
        return [self.name, list(zip(tmp_block, tmp_part_size)), str(self.size)]