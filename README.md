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
