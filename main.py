import mmap
import os
import json
from FileSystem import Node


class FILESYS:
    def __init__(self, _disk='mem.disk', _block_size=4096, _storage_size=2 ** 30):
        self.disk = _disk
        self.nodes = None
        self.tree = None
        self.use = None
        self.block_size = _block_size
        self.storage_size = _storage_size
        self.block_num = self.storage_size // self.block_size
        self.unused_blocks = self.block_num - 2

        # 初始化磁盘
        with open('mem.disk', 'w') as f:
            f.seek(0)
            tmp = {"root": {}}
            text = json.dumps(tmp)
            text += '*' * (self.block_size - len(text))
            f.write(text)
            f.seek(self.block_size)
            tmp = {'root': ['root', [], '0']}
            text = json.dumps(tmp)
            text += '*' * (self.block_size - len(text))
            f.write(text)
            f.seek(self.block_size * 2)
            f.write('*' * (self.block_num - 2) * self.block_size)
        # 映射文件系统
        self._build_file_tree()

    def _get_block(self, start):
        mem = mmap.mmap(os.open(self.disk, os.O_RDWR), (start + 1) * self.block_size)
        info = mem.read()
        mem.close()
        text = bytes.decode(info)[start * self.block_size:]
        return text.rstrip('*')

    def _set_block(self, start, new_buffer: str):
        new_buffer += '*' * (self.block_size - len(new_buffer))
        mem = mmap.mmap(os.open(self.disk, os.O_RDWR), (start + 1) * self.block_size)
        info = mem.read()
        text = bytes.decode(info)
        text = text[:start * self.block_size] + new_buffer
        info = str.encode(text)
        mem.seek(0)
        mem.write(info)
        mem.close()

    def _get_file_tree(self):
        return json.loads(self._get_block(0))

    def _get_file_info(self):
        return json.loads(self._get_block(1))

    def _update_tree(self):
        self._set_block(0, json.dumps(self.tree))
        tmp = {key: self.nodes[key].get_info() for key in self.nodes.keys()}
        self._set_block(1, json.dumps(tmp))

    def _build_file_tree(self):
        self.use = [0] * (self.storage_size // self.block_size)
        self.nodes = {}
        self.tree = self._get_file_tree()
        info = self._get_file_info()
        for path in info.keys():
            node = Node(path)
            node.name = info[path][0]
            node.is_dir = True if info[path][2] == '-1' else False
            if not node.is_dir:
                node.parts = len(info[path][1])
                node.block = [int(part[0]) for part in info[path][1]]
                for part in info[path][1]:
                    self.use[int(part[0])] = 1
                    self.unused_blocs -= 1
                node.part_size = [int(part[1]) for part in info[path][1]]
                node.size = int(info[path][2])
            self.nodes[path] = node

    def ls(self, path: str):
        text = ''
        steps = path.split('/')
        tmp = self.tree[steps[0]]
        for step in steps[1:]:
            tmp = tmp[step]
        for key in tmp.keys():
            node = self.nodes[path + '/' + key]
            is_file = 'dir' if node.is_dir else 'file'
            text += (node.name + '\t' + is_file + '\t%d' % node.size)
            text += '\n'
        return text

    def read(self, path: str):
        node = self.nodes[path]
        parts = node.parts
        text = ''
        for part_index in range(parts):
            used_block = node.block[part_index]
            size = node.part_size[part_index]
            buffer = self._get_block(used_block)
            text += buffer[:size]
        return text

    def new(self, path: str, text: str):
        # 补充：判定剩余空间足够
        use_blocks = len(text) // self.block_size + 1
        if use_blocks > self.unused_blocks:
            raise BlockingIOError
        now_index = 2
        pick_up = []
        remain = len(text) % self.block_size
        sizes = [self.block_size if i != use_blocks - 1 else remain for i in range(use_blocks)]
        for i in range(use_blocks):
            while self.use[now_index] == 1:
                now_index += 1
            self.use[now_index] = 1
            self.unused_blocks -= 1
            start = self.block_size * i
            self._set_block(now_index, text[start:start + sizes[i]])
            pick_up.append(now_index)
        # 文件树更新
        steps = path.split('/')
        tmp = self.tree[steps[0]]
        for step in steps[1:-1]:
            tmp = tmp[step]
        tmp[steps[-1]] = None

        # 文件元数据更新

        new_file = Node(path)
        new_file.name = steps[-1]
        new_file.parts = use_blocks
        new_file.block = pick_up
        new_file.part_size = sizes
        new_file.is_dir = False
        new_file.size = len(text)

        self.nodes[path] = new_file
        self._update_tree()

    def mkdir(self, path: str):
        # 更新文件树
        steps = path.split('/')
        tmp = self.tree[steps[0]]
        for step in steps[1:-1]:
            tmp = tmp[step]
        tmp[steps[-1]] = {}

        # 更新文件元信息
        new_dir = Node(path)
        new_dir.name = steps[-1]
        new_dir.parts = 0
        new_dir.block = []
        new_dir.part_size = []
        new_dir.is_dir = True
        new_dir.size = 0

        self.nodes[path] = new_dir
        self._update_tree()

    def delete(self, path: str):
        if path not in self.nodes.keys():
            raise FileNotFoundError
        # 更新文件树
        steps = path.split('/')
        tmp = self.tree[steps[0]]
        for step in steps[1:-1]:
            tmp = tmp[step]
        tmp.pop(steps[-1])
        # 清理占用
        tmp = self.nodes[path]
        for block in tmp.block:
            self.use[block] = 0
            self.unused_blocs -= 1
        # 更新元数据
        self.nodes.pop(path)

    def write(self, path: str, text: str):
        if path not in self.nodes.keys():
            raise FileNotFoundError
        use_blocks = len(text) // self.block_size + 1
        remain = len(text) % self.block_size
        sizes = [self.block_size if i != use_blocks - 1 else remain for i in range(use_blocks)]

        last_blocks = self.nodes[path].block

        # 修改元数据
        node = self.nodes[path]
        node.size = len(text)
        # 直接写入
        if len(last_blocks) == use_blocks:
            for i in range(len(last_blocks)):
                start = self.block_size * i
                # 修改元数据
                node.part_size[i] = sizes[i]
                self._set_block(last_blocks[i], text[start:start + sizes[i]])

        # 需要全新分配
        elif len(last_blocks) < use_blocks:
            now_index = 2
            self.use[now_index] = 1
            for i in range(len(last_blocks)):
                start = self.block_size * i
                # 修改元数据
                node.part_size[i] = sizes[i]
                self._set_block(last_blocks[i], text[start:start + sizes[i]])
            for i in range(len(last_blocks), use_blocks):
                while self.use[now_index] == 1:
                    now_index += 1
                self.use[now_index] = 1
                self.unused_blocs += 1
                # 修改元数据
                node.block.append(now_index)
                node.part_size.append(sizes[i])
                node.parts += 1
                start = self.block_size * now_index
                self._set_block(now_index, text[start:start + sizes[i]])
        # 需要丢弃块
        else:
            for i in range(use_blocks):
                start = self.block_size * i
                # 修改元数据
                node.part_size[i] = sizes[i]
                self.set_block(last_blocks[i], text[start:start + sizes[i]])
            for i in range(use_blocks, len(last_blocks)):
                # 修改元数据
                index = node.block.index(last_blocks[i])
                node.block.pop(index)
                node.part_size.pop(index)
                node.parts -= 1
                self.use[last_blocks[i]] = 0
                self.unused_blocs -= 1


sys = FILESYS()
# print(sys.ls('root'))
sys.new('root/van', 'my name is van.')
sys.mkdir('root/doc')
print(sys.ls('root'))
print(sys.read('root/van'))
sys.write('root/van', 'I am a performance artist.')
print(sys.read('root/van'))
