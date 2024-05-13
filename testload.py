import xml.etree.ElementTree as ET

# 打开XML文件
tree = ET.parse('E:\\fang_fungus\\2\\8_40_112.xml')
print(tree)
# 获取根元素
root = tree.getroot()
print(root)
