# 使用方法

FILESYS为文件系统类

新建空文件系统

```python
sys = FILESYS()
```

新建文件

```python
sys.new(path, content)
```

新建目录

```
sys.mkdir('root/doc')
```

打印路径

```
print(sys.ls('root'))
```

读取文件

```
print(sys.read('root/van'))
```

重写文件

```
sys.write('root/van', 'I am a performance artist.')
```

删除文件

sys.delete('root/van')

本例中使用json序列化文件树tree和文件元数据nodes
并将其分别存储在第一块和第二块中
文件内容被存储在后面的块中
tree和nodes都由字典嵌套构成，可以方便地修改
由于时间有限，没有考虑到删除目录，删除目录时会发生不可知错误
