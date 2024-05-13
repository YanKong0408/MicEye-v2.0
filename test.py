# import pandas as pd
# import ast
# import cv2
# import xml.etree.ElementTree as ET

# def create_xml(image_path, bounding_boxes, xml_path):
#     root = ET.Element("annotation")

#     img = cv2.imread(image_path)
#     # 创建子元素并添加图像路径信息
#     filename = ET.SubElement(root, "filename")
#     filename.text = image_path[len("E:\\fang_fungus\\4\\"):]
#     filename = ET.SubElement(root, "filename")
#     filename.text = image_path

#     object_elem = ET.SubElement(root, "size")
       
#     name = ET.SubElement(object_elem, "width")
#     name.text = "1024" 

#     name = ET.SubElement(object_elem, "height")
#     name.text = "1024" 

#     name = ET.SubElement(object_elem, "depth")
#     name.text = "3"  

#     # 遍历边界框信息
#     for bbox in bounding_boxes:
#         # 创建object元素
#         # cv2.rectangle(img,(bbox[0],bbox[1]),(bbox[2],bbox[3]),(255,0,0),2)
#         object_elem = ET.SubElement(root, "object")

#         # 创建子元素并添加边界框信息
#         name = ET.SubElement(object_elem, "name")
#         name.text = "fungus" 
#         name = ET.SubElement(object_elem, "pose")
#         name.text = "Unspecified" 
#         name = ET.SubElement(object_elem, "truncated")
#         name.text = "0"  
#         name = ET.SubElement(object_elem, "difficult")
#         name.text = "0"  

#         bndbox = ET.SubElement(object_elem, "bndbox")
#         xmin = ET.SubElement(bndbox, "xmin")
#         xmin.text = str(bbox[0])
#         ymin = ET.SubElement(bndbox, "ymin")
#         ymin.text = str(bbox[1])
#         xmax = ET.SubElement(bndbox, "xmax")
#         xmax.text = str(bbox[2])
#         ymax = ET.SubElement(bndbox, "ymax")
#         ymax.text = str(bbox[3])

#     # 创建XML树
#     tree = ET.ElementTree(root)
#     # cv2.imshow(image_file,img)
#     # cv2.waitKey(0)

#     # 将XML写入文件
#     tree.write(xml_path)



# file_name = 'E:\\fang_fungus\\4_result\\cjd2024-2-1-21-10.csv'
# data = pd.read_csv(file_name,delimiter=";",header=None)
# ind = 0
# for index, row in data.iterrows():
#     bboxs=[]
#     image_file = row[0]
#     raw_boxs = ast.literal_eval(row[3])
#     img = cv2.imread(image_file)
#     for box in raw_boxs:
#         if box[2]>0:
#             w = int(box[2]/box[4])
#             x = int(box[0]/box[4])
#         else:
#             w = -int(box[2]/box[4])
#             x = int((box[0]+box[2])/box[4])

#         if box[3]>0:
#             h = int(box[3]/box[4])
#             y = int(box[1]/box[4])
#         else:
#             h = -int(box[3]/box[4])
#             y = int((box[1]+box[3])/box[4])
        
#         bboxs.append([x,y,x+w,y+h])
        
#     create_xml(image_file, bboxs, image_file.replace('jpg','xml'))


## coco数据集制作
import os
import json
import xml.etree.ElementTree as ET

def xml_to_coco(xml_path, image_id,annotation_id):
    tree = ET.parse(xml_path)
    root = tree.getroot()

    annotation = {
        "id": image_id,
        "file_name": "",
        "width": 0,
        "height": 0,
        "annotations": []
    }

    for elem in root.iter():
        if elem.tag == "filename":
            annotation["file_name"] = elem.text
        elif elem.tag == "width":
            annotation["width"] = int(elem.text)
        elif elem.tag == "height":
            annotation["height"] = int(elem.text)
        elif elem.tag == "object":
            bbox = elem.find("bndbox")
            xmin = int(bbox.find("xmin").text)
            ymin = int(bbox.find("ymin").text)
            xmax = int(bbox.find("xmax").text)
            ymax = int(bbox.find("ymax").text)

            annotation["annotations"].append({
                "id":annotation_id,
                "image_id":image_id,
                "bbox": [xmin, ymin, xmax - xmin, ymax - ymin],
                "category_id": 1  ,
                "area":(xmax-xmin)*(ymax-ymin),
                "iscrowd":0
            })
            annotation_id+=1

    return annotation

def jpg_xml_to_coco(input_dir, output_file):
    images = []
    annotations = []
    categories = [{"id": 1, "name": "fungus"}]  # 设置类别名称，根据实际情况修改

    image_id = 0
    annotation_id = 0

    for filename in os.listdir(input_dir):
        if filename.endswith(".jpg"):
            image_id += 1
            image_path = os.path.join(input_dir, filename)
            xml_path = os.path.join(input_dir, filename.split(".")[0] + ".xml")

            if os.path.exists(xml_path):
                image_info = {
                    "id": image_id,
                    "file_name": image_path,
                    "width": 1024,
                    "height": 1024
                }

                annotation = xml_to_coco(xml_path, image_id,annotation_id)
                annotation_id += len(annotation["annotations"])

                image_info["width"] = annotation["width"]
                image_info["height"] = annotation["height"]

                images.append(image_info)
                annotations.extend(annotation["annotations"])

    coco_data = {
        "images": images,
        "annotations": annotations,
        "categories": categories
    }

    with open(output_file, "w") as f:
        json.dump(coco_data, f)

    print("转换完成！")

# 示例用法
input_dir = "D:\\fungus_cjd\\test"  # 输入文件夹路径
output_file = "D:\\fungus_cjd\\annotations\\test.json"  # 输出JSON文件路径
jpg_xml_to_coco(input_dir, output_file)